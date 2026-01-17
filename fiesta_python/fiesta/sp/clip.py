"""Spatial clipping functions."""

import geopandas as gpd
import rasterio
from rasterio.mask import mask
from shapely.geometry import box
import numpy as np
from pathlib import Path
from typing import Optional, Union, Tuple

from fiesta.utils import DataValidationError


def clip_poly(
    gdf: gpd.GeoDataFrame,
    clip_boundary: Union[gpd.GeoDataFrame, str, Path],
    keep_intersecting: bool = True,
) -> gpd.GeoDataFrame:
    """
    Clip polygon/point features by boundary.
    
    Args:
        gdf: GeoDataFrame to clip
        clip_boundary: Boundary GeoDataFrame or path to boundary file
        keep_intersecting: If True, keep features that intersect boundary
        
    Returns:
        Clipped GeoDataFrame
        
    Examples:
        >>> # Clip plots by study area
        >>> clipped_plots = clip_poly(plots_gdf, study_area_gdf)
        
        >>> # Clip stands by administrative boundary
        >>> clipped_stands = clip_poly(
        ...     stands_gdf,
        ...     "boundaries/county.shp"
        ... )
    """
    if not isinstance(gdf, gpd.GeoDataFrame):
        raise DataValidationError("Input must be a GeoDataFrame")
    
    # Load boundary if path provided
    if isinstance(clip_boundary, (str, Path)):
        from fiesta.sp.import_spatial import import_spatial
        clip_boundary = import_spatial(clip_boundary)
    
    if not isinstance(clip_boundary, gpd.GeoDataFrame):
        raise DataValidationError("clip_boundary must be a GeoDataFrame or file path")
    
    # Ensure same CRS
    if gdf.crs != clip_boundary.crs:
        clip_boundary = clip_boundary.to_crs(gdf.crs)
    
    # Clip features
    if keep_intersecting:
        # Keep all features that intersect the boundary
        clipped = gpd.clip(gdf, clip_boundary)
    else:
        # Only keep features completely within boundary
        # Create union of clip boundary
        clip_union = clip_boundary.geometry.unary_union
        within_mask = gdf.geometry.within(clip_union)
        clipped = gdf[within_mask].copy()
    
    return clipped


def clip_point(
    points_gdf: gpd.GeoDataFrame,
    clip_boundary: Union[gpd.GeoDataFrame, str, Path],
) -> gpd.GeoDataFrame:
    """
    Clip point features by boundary.
    
    Args:
        points_gdf: GeoDataFrame with point geometries
        clip_boundary: Boundary GeoDataFrame or path to boundary file
        
    Returns:
        Clipped GeoDataFrame with points within boundary
        
    Examples:
        >>> # Clip FIA plots by state boundary
        >>> plots_in_state = clip_point(plots_gdf, state_boundary)
    """
    return clip_poly(points_gdf, clip_boundary, keep_intersecting=False)


def clip_raster(
    raster_path: Union[str, Path],
    clip_boundary: Union[gpd.GeoDataFrame, str, Path],
    output_path: Optional[Union[str, Path]] = None,
    crop: bool = True,
    all_touched: bool = False,
) -> Union[Tuple[np.ndarray, dict], str]:
    """
    Clip raster by polygon boundary.
    
    Args:
        raster_path: Path to input raster file
        clip_boundary: Boundary GeoDataFrame or path to boundary file
        output_path: Optional path to save clipped raster
        crop: If True, crop raster extent to boundary
        all_touched: If True, include pixels touched by boundary
        
    Returns:
        If output_path is None: tuple of (clipped_array, metadata)
        If output_path provided: path to output file
        
    Examples:
        >>> # Clip elevation raster by study area
        >>> clipped_data, meta = clip_raster(
        ...     "elevation.tif",
        ...     study_area_gdf
        ... )
        
        >>> # Clip and save to file
        >>> output_file = clip_raster(
        ...     "landcover.tif",
        ...     "boundary.shp",
        ...     output_path="landcover_clipped.tif"
        ... )
    """
    # Load boundary if path provided
    if isinstance(clip_boundary, (str, Path)):
        from fiesta.sp.import_spatial import import_spatial
        clip_boundary = import_spatial(clip_boundary)
    
    if not isinstance(clip_boundary, gpd.GeoDataFrame):
        raise DataValidationError("clip_boundary must be a GeoDataFrame or file path")
    
    # Open raster
    with rasterio.open(raster_path) as src:
        # Reproject boundary to raster CRS if needed
        if clip_boundary.crs != src.crs:
            clip_boundary = clip_boundary.to_crs(src.crs)
        
        # Get geometries for masking
        geoms = clip_boundary.geometry.values
        
        # Clip raster
        try:
            clipped_data, clipped_transform = mask(
                src,
                geoms,
                crop=crop,
                all_touched=all_touched,
                nodata=src.nodata,
            )
        except Exception as e:
            raise DataValidationError(f"Failed to clip raster: {e}")
        
        # Update metadata
        clipped_meta = src.meta.copy()
        clipped_meta.update({
            "driver": "GTiff",
            "height": clipped_data.shape[1],
            "width": clipped_data.shape[2],
            "transform": clipped_transform,
        })
    
    # Save to file if output path provided
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with rasterio.open(output_path, "w", **clipped_meta) as dest:
            dest.write(clipped_data)
        
        return str(output_path)
    else:
        return clipped_data, clipped_meta


def clip_by_bbox(
    gdf: gpd.GeoDataFrame,
    bbox: Tuple[float, float, float, float],
) -> gpd.GeoDataFrame:
    """
    Clip features by bounding box.
    
    Args:
        gdf: GeoDataFrame to clip
        bbox: Bounding box as (minx, miny, maxx, maxy)
        
    Returns:
        Clipped GeoDataFrame
        
    Examples:
        >>> # Clip by bounding box
        >>> bbox = (-111.0, 41.0, -109.0, 43.0)  # Wyoming area
        >>> clipped = clip_by_bbox(plots_gdf, bbox)
    """
    # Create polygon from bbox
    bbox_poly = box(*bbox)
    bbox_gdf = gpd.GeoDataFrame(
        {'geometry': [bbox_poly]},
        crs=gdf.crs
    )
    
    return clip_poly(gdf, bbox_gdf)
