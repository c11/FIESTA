"""Spatial extraction functions for raster and polygon data."""

import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
import numpy as np
from pathlib import Path
from typing import Optional, Union, List, Dict, Any
import pandas as pd

from fiesta.utils import DataValidationError, check_dataframe


def extract_raster(
    points_gdf: gpd.GeoDataFrame,
    raster_path: Union[str, Path],
    band: int = 1,
    output_col: Optional[str] = None,
    buffer: Optional[float] = None,
    aggfunc: str = "mean",
) -> gpd.GeoDataFrame:
    """
    Extract raster values at point locations.
    
    Args:
        points_gdf: GeoDataFrame with point geometries
        raster_path: Path to raster file
        band: Band number to extract (1-indexed)
        output_col: Name for output column (auto-generated if None)
        buffer: Optional buffer distance around points for zonal statistics
        aggfunc: Aggregation function for buffered extraction ('mean', 'median', 'sum', etc.)
        
    Returns:
        GeoDataFrame with extracted raster values added as new column
        
    Examples:
        >>> # Extract elevation at plot locations
        >>> plots_with_elev = extract_raster(
        ...     plots_gdf,
        ...     "elevation.tif",
        ...     output_col="ELEVATION"
        ... )
        
        >>> # Extract mean slope in 30m buffer around plots
        >>> plots_with_slope = extract_raster(
        ...     plots_gdf,
        ...     "slope.tif",
        ...     output_col="SLOPE_MEAN",
        ...     buffer=30,
        ...     aggfunc="mean"
        ... )
    """
    if not isinstance(points_gdf, gpd.GeoDataFrame):
        raise DataValidationError("Input must be a GeoDataFrame")
    
    # Generate output column name if not provided
    if output_col is None:
        raster_name = Path(raster_path).stem
        output_col = f"{raster_name}_band{band}"
    
    # Make a copy
    result = points_gdf.copy()
    
    # Open raster
    with rasterio.open(raster_path) as src:
        # Reproject points to raster CRS if needed
        if points_gdf.crs != src.crs:
            points_reproj = points_gdf.to_crs(src.crs)
        else:
            points_reproj = points_gdf
        
        # Extract values
        if buffer is None:
            # Point extraction
            coords = [(geom.x, geom.y) for geom in points_reproj.geometry]
            values = [x[0] for x in src.sample(coords, band)]
            
            # Convert nodata to NaN
            values = np.array(values, dtype=float)
            if src.nodata is not None:
                values[values == src.nodata] = np.nan
            
            result[output_col] = values
        else:
            # Buffered extraction (zonal stats)
            values = []
            
            # Buffer points
            buffered = points_reproj.geometry.buffer(buffer)
            
            for geom in buffered:
                # Read raster data within geometry
                try:
                    masked_data, _ = rasterio.mask.mask(
                        src,
                        [geom],
                        crop=True,
                        nodata=src.nodata,
                        indexes=band,
                    )
                    
                    # Remove nodata values
                    valid_data = masked_data[masked_data != src.nodata]
                    
                    if len(valid_data) == 0:
                        values.append(np.nan)
                    else:
                        # Apply aggregation function
                        if aggfunc == "mean":
                            values.append(np.mean(valid_data))
                        elif aggfunc == "median":
                            values.append(np.median(valid_data))
                        elif aggfunc == "sum":
                            values.append(np.sum(valid_data))
                        elif aggfunc == "min":
                            values.append(np.min(valid_data))
                        elif aggfunc == "max":
                            values.append(np.max(valid_data))
                        elif aggfunc == "std":
                            values.append(np.std(valid_data))
                        else:
                            raise ValueError(f"Unknown aggfunc: {aggfunc}")
                
                except Exception:
                    values.append(np.nan)
            
            result[output_col] = values
    
    return result


def extract_poly(
    points_gdf: gpd.GeoDataFrame,
    poly_gdf: Union[gpd.GeoDataFrame, str, Path],
    attributes: Optional[List[str]] = None,
    spatial_join_type: str = "intersects",
) -> gpd.GeoDataFrame:
    """
    Extract polygon attributes at point locations using spatial join.
    
    Args:
        points_gdf: GeoDataFrame with point geometries
        poly_gdf: GeoDataFrame with polygon geometries or path to polygon file
        attributes: List of attribute columns to extract (None for all)
        spatial_join_type: Type of spatial join ('intersects', 'within', 'contains')
        
    Returns:
        GeoDataFrame with polygon attributes joined to points
        
    Examples:
        >>> # Extract forest type from stand polygons
        >>> plots_with_stands = extract_poly(
        ...     plots_gdf,
        ...     stands_gdf,
        ...     attributes=['FORTYPCD', 'STDSZCD']
        ... )
        
        >>> # Extract administrative unit
        >>> plots_with_admin = extract_poly(
        ...     plots_gdf,
        ...     "admin_boundaries.shp",
        ...     attributes=['COUNTY', 'STATE']
        ... )
    """
    if not isinstance(points_gdf, gpd.GeoDataFrame):
        raise DataValidationError("points_gdf must be a GeoDataFrame")
    
    # Load polygon data if path provided
    if isinstance(poly_gdf, (str, Path)):
        from fiesta.sp.import_spatial import import_spatial
        poly_gdf = import_spatial(poly_gdf)
    
    if not isinstance(poly_gdf, gpd.GeoDataFrame):
        raise DataValidationError("poly_gdf must be a GeoDataFrame or file path")
    
    # Select attributes to keep
    if attributes is not None:
        # Keep geometry and specified attributes
        poly_cols = ['geometry'] + [col for col in attributes if col in poly_gdf.columns]
        poly_gdf = poly_gdf[poly_cols].copy()
    
    # Ensure same CRS
    if points_gdf.crs != poly_gdf.crs:
        poly_gdf = poly_gdf.to_crs(points_gdf.crs)
    
    # Spatial join
    result = gpd.sjoin(
        points_gdf,
        poly_gdf,
        how="left",
        predicate=spatial_join_type,
    )
    
    # Remove index column from join
    if 'index_right' in result.columns:
        result = result.drop(columns=['index_right'])
    
    return result


def extract_multiple_rasters(
    points_gdf: gpd.GeoDataFrame,
    raster_dict: Dict[str, Union[str, Path]],
    band: int = 1,
    buffer: Optional[float] = None,
    aggfunc: str = "mean",
) -> gpd.GeoDataFrame:
    """
    Extract values from multiple rasters at point locations.
    
    Args:
        points_gdf: GeoDataFrame with point geometries
        raster_dict: Dictionary mapping output column names to raster paths
        band: Band number to extract from all rasters
        buffer: Optional buffer distance for zonal statistics
        aggfunc: Aggregation function for buffered extraction
        
    Returns:
        GeoDataFrame with values extracted from all rasters
        
    Examples:
        >>> # Extract multiple environmental variables
        >>> rasters = {
        ...     'ELEVATION': 'elevation.tif',
        ...     'SLOPE': 'slope.tif',
        ...     'ASPECT': 'aspect.tif',
        ...     'LANDCOVER': 'landcover.tif',
        ... }
        >>> plots_with_vars = extract_multiple_rasters(
        ...     plots_gdf,
        ...     rasters
        ... )
    """
    result = points_gdf.copy()
    
    for output_col, raster_path in raster_dict.items():
        result = extract_raster(
            result,
            raster_path,
            band=band,
            output_col=output_col,
            buffer=buffer,
            aggfunc=aggfunc,
        )
    
    return result


def sample_raster_by_polygons(
    poly_gdf: gpd.GeoDataFrame,
    raster_path: Union[str, Path],
    stats: List[str] = ["mean", "sum", "count"],
    band: int = 1,
) -> gpd.GeoDataFrame:
    """
    Calculate zonal statistics for raster within polygons.
    
    Args:
        poly_gdf: GeoDataFrame with polygon geometries
        raster_path: Path to raster file
        stats: List of statistics to calculate
        band: Band number to process
        
    Returns:
        GeoDataFrame with zonal statistics added as columns
        
    Examples:
        >>> # Calculate mean elevation per stand
        >>> stands_with_elev = sample_raster_by_polygons(
        ...     stands_gdf,
        ...     "elevation.tif",
        ...     stats=["mean", "min", "max", "std"]
        ... )
    """
    result = poly_gdf.copy()
    raster_name = Path(raster_path).stem
    
    with rasterio.open(raster_path) as src:
        # Reproject polygons if needed
        if poly_gdf.crs != src.crs:
            poly_reproj = poly_gdf.to_crs(src.crs)
        else:
            poly_reproj = poly_gdf
        
        # Calculate statistics for each polygon
        for stat in stats:
            col_name = f"{raster_name}_{stat}"
            result[col_name] = None
        
        for idx, geom in enumerate(poly_reproj.geometry):
            try:
                # Mask raster by polygon
                masked_data, _ = rasterio.mask.mask(
                    src,
                    [geom],
                    crop=True,
                    nodata=src.nodata,
                    indexes=band,
                )
                
                # Remove nodata
                valid_data = masked_data[masked_data != src.nodata]
                
                if len(valid_data) > 0:
                    for stat in stats:
                        col_name = f"{raster_name}_{stat}"
                        if stat == "mean":
                            result.at[idx, col_name] = np.mean(valid_data)
                        elif stat == "median":
                            result.at[idx, col_name] = np.median(valid_data)
                        elif stat == "sum":
                            result.at[idx, col_name] = np.sum(valid_data)
                        elif stat == "min":
                            result.at[idx, col_name] = np.min(valid_data)
                        elif stat == "max":
                            result.at[idx, col_name] = np.max(valid_data)
                        elif stat == "std":
                            result.at[idx, col_name] = np.std(valid_data)
                        elif stat == "count":
                            result.at[idx, col_name] = len(valid_data)
            except Exception:
                # Leave as None if extraction fails
                pass
    
    return result
