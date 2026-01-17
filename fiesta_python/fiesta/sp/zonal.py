"""Zonal statistics functions for raster data."""

import geopandas as gpd
import rasterio
import numpy as np
from pathlib import Path
from typing import Optional, Union, List, Dict
import pandas as pd

from fiesta.utils import DataValidationError


def zonal_stats(
    zones_gdf: gpd.GeoDataFrame,
    raster_path: Union[str, Path],
    stats: List[str] = ["mean", "sum", "count"],
    band: int = 1,
    prefix: Optional[str] = None,
    categorical: bool = False,
) -> gpd.GeoDataFrame:
    """
    Calculate zonal statistics for raster within polygon zones.
    
    Args:
        zones_gdf: GeoDataFrame with polygon zones
        raster_path: Path to raster file
        stats: List of statistics to calculate
            For continuous: 'mean', 'median', 'sum', 'std', 'min', 'max', 'count'
            For categorical: 'majority', 'minority', 'unique', 'mode'
        band: Band number to process (1-indexed)
        prefix: Prefix for output column names
        categorical: If True, treat raster as categorical
        
    Returns:
        GeoDataFrame with zonal statistics added as columns
        
    Examples:
        >>> # Calculate elevation statistics per stand
        >>> stands_with_elev = zonal_stats(
        ...     stands_gdf,
        ...     "elevation.tif",
        ...     stats=["mean", "min", "max", "std"],
        ...     prefix="elev"
        ... )
        
        >>> # Calculate area by land cover class
        >>> stands_with_lc = zonal_stats(
        ...     stands_gdf,
        ...     "landcover.tif",
        ...     stats=["majority", "count"],
        ...     categorical=True,
        ...     prefix="lc"
        ... )
    """
    if not isinstance(zones_gdf, gpd.GeoDataFrame):
        raise DataValidationError("zones_gdf must be a GeoDataFrame")
    
    result = zones_gdf.copy()
    
    # Generate prefix if not provided
    if prefix is None:
        prefix = Path(raster_path).stem
    
    # Initialize columns
    for stat in stats:
        col_name = f"{prefix}_{stat}"
        result[col_name] = None
    
    # Open raster
    with rasterio.open(raster_path) as src:
        # Reproject zones if needed
        if zones_gdf.crs != src.crs:
            zones_reproj = zones_gdf.to_crs(src.crs)
        else:
            zones_reproj = zones_gdf
        
        # Process each zone
        for idx, geom in enumerate(zones_reproj.geometry):
            try:
                # Mask raster by zone
                masked_data, _ = rasterio.mask.mask(
                    src,
                    [geom],
                    crop=True,
                    nodata=src.nodata,
                    indexes=band,
                )
                
                # Flatten and remove nodata
                data = masked_data.flatten()
                if src.nodata is not None:
                    data = data[data != src.nodata]
                
                if len(data) == 0:
                    continue
                
                # Calculate statistics
                for stat in stats:
                    col_name = f"{prefix}_{stat}"
                    
                    if categorical:
                        # Categorical statistics
                        if stat == "majority" or stat == "mode":
                            # Most common value
                            values, counts = np.unique(data, return_counts=True)
                            result.at[idx, col_name] = values[np.argmax(counts)]
                        elif stat == "minority":
                            # Least common value
                            values, counts = np.unique(data, return_counts=True)
                            result.at[idx, col_name] = values[np.argmin(counts)]
                        elif stat == "unique":
                            # Number of unique values
                            result.at[idx, col_name] = len(np.unique(data))
                        elif stat == "count":
                            # Total count of pixels
                            result.at[idx, col_name] = len(data)
                    else:
                        # Continuous statistics
                        if stat == "mean":
                            result.at[idx, col_name] = np.mean(data)
                        elif stat == "median":
                            result.at[idx, col_name] = np.median(data)
                        elif stat == "sum":
                            result.at[idx, col_name] = np.sum(data)
                        elif stat == "min":
                            result.at[idx, col_name] = np.min(data)
                        elif stat == "max":
                            result.at[idx, col_name] = np.max(data)
                        elif stat == "std":
                            result.at[idx, col_name] = np.std(data)
                        elif stat == "var":
                            result.at[idx, col_name] = np.var(data)
                        elif stat == "count":
                            result.at[idx, col_name] = len(data)
                        elif stat == "range":
                            result.at[idx, col_name] = np.ptp(data)
                        elif stat.startswith("percentile_"):
                            # e.g., "percentile_25" for 25th percentile
                            pct = float(stat.split("_")[1])
                            result.at[idx, col_name] = np.percentile(data, pct)
                
            except Exception as e:
                # Leave as None if processing fails
                pass
    
    return result


def zonal_histogram(
    zones_gdf: gpd.GeoDataFrame,
    raster_path: Union[str, Path],
    bins: Optional[Union[int, List[float]]] = None,
    band: int = 1,
) -> Dict[int, np.ndarray]:
    """
    Calculate histogram of raster values within each zone.
    
    Args:
        zones_gdf: GeoDataFrame with polygon zones
        raster_path: Path to raster file
        bins: Number of bins or list of bin edges
        band: Band number to process
        
    Returns:
        Dictionary mapping zone index to histogram counts
        
    Examples:
        >>> # Calculate elevation distribution per stand
        >>> histograms = zonal_histogram(
        ...     stands_gdf,
        ...     "elevation.tif",
        ...     bins=20
        ... )
    """
    if not isinstance(zones_gdf, gpd.GeoDataFrame):
        raise DataValidationError("zones_gdf must be a GeoDataFrame")
    
    histograms = {}
    
    with rasterio.open(raster_path) as src:
        # Reproject zones if needed
        if zones_gdf.crs != src.crs:
            zones_reproj = zones_gdf.to_crs(src.crs)
        else:
            zones_reproj = zones_gdf
        
        # Process each zone
        for idx, geom in enumerate(zones_reproj.geometry):
            try:
                # Mask raster by zone
                masked_data, _ = rasterio.mask.mask(
                    src,
                    [geom],
                    crop=True,
                    nodata=src.nodata,
                    indexes=band,
                )
                
                # Flatten and remove nodata
                data = masked_data.flatten()
                if src.nodata is not None:
                    data = data[data != src.nodata]
                
                if len(data) > 0:
                    # Calculate histogram
                    hist, bin_edges = np.histogram(data, bins=bins)
                    histograms[idx] = {
                        'counts': hist,
                        'bin_edges': bin_edges,
                    }
            except Exception:
                pass
    
    return histograms


def zonal_area_by_class(
    zones_gdf: gpd.GeoDataFrame,
    raster_path: Union[str, Path],
    pixel_area: Optional[float] = None,
    band: int = 1,
) -> pd.DataFrame:
    """
    Calculate area by class within each zone for categorical raster.
    
    Args:
        zones_gdf: GeoDataFrame with polygon zones
        raster_path: Path to categorical raster
        pixel_area: Area of each pixel (if None, calculated from raster)
        band: Band number to process
        
    Returns:
        DataFrame with zone index, class value, and area
        
    Examples:
        >>> # Calculate forest area by type per county
        >>> area_by_type = zonal_area_by_class(
        ...     counties_gdf,
        ...     "forest_type.tif"
        ... )
    """
    results = []
    
    with rasterio.open(raster_path) as src:
        # Calculate pixel area if not provided
        if pixel_area is None:
            # Assumes equal area pixels (works for projected CRS)
            transform = src.transform
            pixel_area = abs(transform.a * transform.e)
        
        # Reproject zones if needed
        if zones_gdf.crs != src.crs:
            zones_reproj = zones_gdf.to_crs(src.crs)
        else:
            zones_reproj = zones_gdf
        
        # Process each zone
        for idx, geom in enumerate(zones_reproj.geometry):
            try:
                # Mask raster by zone
                masked_data, _ = rasterio.mask.mask(
                    src,
                    [geom],
                    crop=True,
                    nodata=src.nodata,
                    indexes=band,
                )
                
                # Flatten and remove nodata
                data = masked_data.flatten()
                if src.nodata is not None:
                    data = data[data != src.nodata]
                
                if len(data) > 0:
                    # Count pixels by class
                    values, counts = np.unique(data, return_counts=True)
                    
                    # Calculate area
                    for value, count in zip(values, counts):
                        results.append({
                            'zone_id': idx,
                            'class_value': int(value),
                            'pixel_count': int(count),
                            'area': count * pixel_area,
                        })
            except Exception:
                pass
    
    return pd.DataFrame(results)


def tabulate_area(
    zones_gdf: gpd.GeoDataFrame,
    raster_path: Union[str, Path],
    zone_id_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Create cross-tabulation of zone IDs vs raster classes with areas.
    
    Args:
        zones_gdf: GeoDataFrame with polygon zones
        raster_path: Path to categorical raster
        zone_id_col: Column name for zone identifier
        
    Returns:
        DataFrame with zones as rows and classes as columns
        
    Examples:
        >>> # Tabulate land cover by management unit
        >>> lc_table = tabulate_area(
        ...     units_gdf,
        ...     "landcover.tif",
        ...     zone_id_col="UNIT_ID"
        ... )
    """
    # Get area by class for each zone
    area_df = zonal_area_by_class(zones_gdf, raster_path)
    
    if area_df.empty:
        return pd.DataFrame()
    
    # Pivot to wide format
    pivot_df = area_df.pivot(
        index='zone_id',
        columns='class_value',
        values='area'
    ).fillna(0)
    
    # Add zone identifier if provided
    if zone_id_col and zone_id_col in zones_gdf.columns:
        pivot_df[zone_id_col] = zones_gdf[zone_id_col].values
        pivot_df = pivot_df.set_index(zone_id_col)
    
    # Rename columns to include class prefix
    pivot_df.columns = [f"class_{int(col)}" for col in pivot_df.columns]
    
    return pivot_df
