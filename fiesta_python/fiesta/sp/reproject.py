"""Spatial reprojection functions."""

import geopandas as gpd
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from pathlib import Path
from typing import Optional, Union
import warnings

from fiesta.utils import DataValidationError


def reproject_vector(
    gdf: gpd.GeoDataFrame,
    target_crs: Union[str, int],
    preserve_columns: bool = True,
) -> gpd.GeoDataFrame:
    """
    Reproject vector data to a different coordinate reference system.
    
    Args:
        gdf: GeoDataFrame to reproject
        target_crs: Target CRS (EPSG code, proj4 string, or WKT)
        preserve_columns: If True, preserve all attribute columns
        
    Returns:
        Reprojected GeoDataFrame
        
    Examples:
        >>> # Reproject from WGS84 to UTM Zone 12N
        >>> utm_gdf = reproject_vector(gdf, 'EPSG:32612')
        
        >>> # Reproject using EPSG code
        >>> albers_gdf = reproject_vector(gdf, 5070)  # NAD83 Albers
        
        >>> # Reproject to match another dataset
        >>> matched_gdf = reproject_vector(gdf, reference_gdf.crs)
    """
    if not isinstance(gdf, gpd.GeoDataFrame):
        raise DataValidationError("Input must be a GeoDataFrame")
    
    if gdf.crs is None:
        warnings.warn("Input GeoDataFrame has no CRS defined")
        return gdf
    
    # Reproject
    reprojected = gdf.to_crs(target_crs)
    
    return reprojected


def reproject_raster(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    target_crs: Union[str, int],
    resampling_method: str = "nearest",
    nodata: Optional[float] = None,
) -> str:
    """
    Reproject raster to a different coordinate reference system.
    
    Args:
        input_path: Path to input raster
        output_path: Path for output raster
        target_crs: Target CRS (EPSG code or proj4 string)
        resampling_method: Resampling method for reprojection
            Options: 'nearest', 'bilinear', 'cubic', 'cubic_spline', 'lanczos',
                    'average', 'mode', 'max', 'min', 'med', 'q1', 'q3'
        nodata: NoData value for output raster
        
    Returns:
        Path to output raster
        
    Examples:
        >>> # Reproject elevation raster to UTM
        >>> output = reproject_raster(
        ...     "elevation_wgs84.tif",
        ...     "elevation_utm.tif",
        ...     'EPSG:32612',
        ...     resampling_method='bilinear'
        ... )
        
        >>> # Reproject categorical raster (use nearest neighbor)
        >>> output = reproject_raster(
        ...     "landcover.tif",
        ...     "landcover_albers.tif",
        ...     5070,
        ...     resampling_method='nearest'
        ... )
    """
    # Map resampling method names to rasterio constants
    resampling_map = {
        'nearest': Resampling.nearest,
        'bilinear': Resampling.bilinear,
        'cubic': Resampling.cubic,
        'cubic_spline': Resampling.cubic_spline,
        'lanczos': Resampling.lanczos,
        'average': Resampling.average,
        'mode': Resampling.mode,
        'max': Resampling.max,
        'min': Resampling.min,
        'med': Resampling.med,
        'q1': Resampling.q1,
        'q3': Resampling.q3,
    }
    
    if resampling_method not in resampling_map:
        raise ValueError(
            f"Invalid resampling method '{resampling_method}'. "
            f"Choose from: {list(resampling_map.keys())}"
        )
    
    resampling = resampling_map[resampling_method]
    
    # Ensure output directory exists
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Open source raster
    with rasterio.open(input_path) as src:
        # Convert target_crs to CRS object
        if isinstance(target_crs, int):
            target_crs = f"EPSG:{target_crs}"
        
        # Calculate transform and dimensions for output
        transform, width, height = calculate_default_transform(
            src.crs,
            target_crs,
            src.width,
            src.height,
            *src.bounds
        )
        
        # Update metadata
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': target_crs,
            'transform': transform,
            'width': width,
            'height': height,
        })
        
        if nodata is not None:
            kwargs['nodata'] = nodata
        
        # Write reprojected raster
        with rasterio.open(output_path, 'w', **kwargs) as dst:
            for band_idx in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, band_idx),
                    destination=rasterio.band(dst, band_idx),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=target_crs,
                    resampling=resampling,
                )
    
    return str(output_path)


def match_crs(
    gdf: gpd.GeoDataFrame,
    reference: Union[gpd.GeoDataFrame, str],
) -> gpd.GeoDataFrame:
    """
    Reproject GeoDataFrame to match CRS of reference dataset.
    
    Args:
        gdf: GeoDataFrame to reproject
        reference: Reference GeoDataFrame or CRS string
        
    Returns:
        Reprojected GeoDataFrame
        
    Examples:
        >>> # Match CRS to another dataset
        >>> matched = match_crs(plots_gdf, boundary_gdf)
    """
    if isinstance(reference, gpd.GeoDataFrame):
        target_crs = reference.crs
    else:
        target_crs = reference
    
    if gdf.crs == target_crs:
        return gdf
    
    return reproject_vector(gdf, target_crs)


def get_utm_crs(longitude: float, latitude: float) -> str:
    """
    Get appropriate UTM zone CRS for given coordinates.
    
    Args:
        longitude: Longitude in degrees
        latitude: Latitude in degrees
        
    Returns:
        EPSG code string for UTM zone
        
    Examples:
        >>> # Get UTM zone for Wyoming
        >>> utm_crs = get_utm_crs(-107.5, 43.0)
        >>> print(utm_crs)  # 'EPSG:32612' (UTM Zone 12N)
    """
    # Calculate UTM zone
    utm_zone = int((longitude + 180) / 6) + 1
    
    # Determine hemisphere
    if latitude >= 0:
        # Northern hemisphere
        epsg_code = 32600 + utm_zone
    else:
        # Southern hemisphere
        epsg_code = 32700 + utm_zone
    
    return f"EPSG:{epsg_code}"


def reproject_to_utm(
    gdf: gpd.GeoDataFrame,
    centroid_based: bool = True,
) -> gpd.GeoDataFrame:
    """
    Reproject GeoDataFrame to appropriate UTM zone.
    
    Args:
        gdf: GeoDataFrame to reproject
        centroid_based: If True, determine UTM zone from data centroid
        
    Returns:
        Reprojected GeoDataFrame in UTM
        
    Examples:
        >>> # Reproject to UTM using data centroid
        >>> utm_gdf = reproject_to_utm(gdf)
    """
    if gdf.crs is None:
        raise DataValidationError("Input GeoDataFrame must have a CRS defined")
    
    # Get centroid in WGS84
    if gdf.crs != "EPSG:4326":
        gdf_wgs84 = gdf.to_crs("EPSG:4326")
    else:
        gdf_wgs84 = gdf
    
    if centroid_based:
        # Use centroid of all features
        centroid = gdf_wgs84.geometry.unary_union.centroid
        lon, lat = centroid.x, centroid.y
    else:
        # Use center of bounds
        bounds = gdf_wgs84.total_bounds
        lon = (bounds[0] + bounds[2]) / 2
        lat = (bounds[1] + bounds[3]) / 2
    
    # Get appropriate UTM CRS
    utm_crs = get_utm_crs(lon, lat)
    
    # Reproject
    return reproject_vector(gdf, utm_crs)
