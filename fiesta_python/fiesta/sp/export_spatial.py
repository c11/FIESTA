"""Spatial data export functions."""

import geopandas as gpd
from pathlib import Path
from typing import Optional, Union
import warnings

from fiesta.utils import DataValidationError


def export_spatial(
    gdf: gpd.GeoDataFrame,
    output_path: Union[str, Path],
    driver: Optional[str] = None,
    layer: Optional[str] = None,
    overwrite: bool = False,
    verbose: bool = True,
) -> str:
    """
    Export GeoDataFrame to spatial file format.
    
    Args:
        gdf: GeoDataFrame to export
        output_path: Output file path
        driver: GDAL driver name (auto-detected from extension if None)
        layer: Layer name (for multi-layer formats like GeoPackage)
        overwrite: If True, overwrite existing file
        verbose: If True, print information messages
        
    Returns:
        Path to exported file
        
    Raises:
        DataValidationError: If export fails
        
    Examples:
        >>> # Export to shapefile
        >>> export_spatial(gdf, "output/boundary.shp")
        
        >>> # Export to GeoPackage with layer name
        >>> export_spatial(
        ...     gdf,
        ...     "output/fia_data.gpkg",
        ...     layer="plots"
        ... )
        
        >>> # Export to GeoJSON
        >>> export_spatial(gdf, "output/features.geojson")
    """
    if not isinstance(gdf, gpd.GeoDataFrame):
        raise DataValidationError("Input must be a GeoDataFrame")
    
    if gdf.empty:
        warnings.warn("GeoDataFrame is empty, nothing to export")
        return str(output_path)
    
    output_path = Path(output_path)
    
    # Check if file exists
    if output_path.exists() and not overwrite:
        raise DataValidationError(
            f"Output file already exists: {output_path}. "
            "Set overwrite=True to replace."
        )
    
    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Auto-detect driver from extension
    if driver is None:
        ext = output_path.suffix.lower()
        driver_map = {
            '.shp': 'ESRI Shapefile',
            '.gpkg': 'GPKG',
            '.geojson': 'GeoJSON',
            '.json': 'GeoJSON',
            '.kml': 'KML',
            '.gml': 'GML',
        }
        driver = driver_map.get(ext)
        
        if driver is None:
            warnings.warn(
                f"Could not auto-detect driver for extension '{ext}', "
                "using default (GeoJSON)"
            )
            driver = 'GeoJSON'
    
    # Export
    try:
        gdf.to_file(
            output_path,
            driver=driver,
            layer=layer,
        )
        
        if verbose:
            print(f"Exported {len(gdf)} features to {output_path}")
            print(f"Driver: {driver}")
            if layer:
                print(f"Layer: {layer}")
    
    except Exception as e:
        raise DataValidationError(f"Failed to export spatial data: {e}")
    
    return str(output_path)


def export_to_geojson(
    gdf: gpd.GeoDataFrame,
    output_path: Union[str, Path],
    drop_na_geometry: bool = True,
) -> str:
    """
    Export GeoDataFrame to GeoJSON format.
    
    Args:
        gdf: GeoDataFrame to export
        output_path: Output GeoJSON file path
        drop_na_geometry: If True, remove features with null geometry
        
    Returns:
        Path to exported file
    """
    if drop_na_geometry:
        gdf = gdf[gdf.geometry.notna()].copy()
    
    return export_spatial(
        gdf,
        output_path,
        driver='GeoJSON'
    )


def export_to_shapefile(
    gdf: gpd.GeoDataFrame,
    output_path: Union[str, Path],
    encoding: str = 'utf-8',
) -> str:
    """
    Export GeoDataFrame to ESRI Shapefile format.
    
    Args:
        gdf: GeoDataFrame to export
        output_path: Output shapefile path (.shp)
        encoding: Character encoding for attribute data
        
    Returns:
        Path to exported file
        
    Note:
        Shapefile has limitations:
        - Column names limited to 10 characters
        - No support for datetime fields
        - Single geometry type per file
    """
    # Ensure .shp extension
    output_path = Path(output_path)
    if output_path.suffix.lower() != '.shp':
        output_path = output_path.with_suffix('.shp')
    
    return export_spatial(
        gdf,
        output_path,
        driver='ESRI Shapefile'
    )


def export_to_geopackage(
    gdf: gpd.GeoDataFrame,
    output_path: Union[str, Path],
    layer: str = 'features',
    append: bool = False,
) -> str:
    """
    Export GeoDataFrame to GeoPackage format.
    
    Args:
        gdf: GeoDataFrame to export
        output_path: Output GeoPackage path (.gpkg)
        layer: Layer name within the GeoPackage
        append: If True, append to existing layer
        
    Returns:
        Path to exported file
        
    Note:
        GeoPackage is recommended over Shapefile as it:
        - Supports longer field names
        - Handles multiple layers in one file
        - Better supports datetime and complex types
    """
    # Ensure .gpkg extension
    output_path = Path(output_path)
    if output_path.suffix.lower() != '.gpkg':
        output_path = output_path.with_suffix('.gpkg')
    
    mode = 'a' if append else 'w'
    
    gdf.to_file(
        output_path,
        driver='GPKG',
        layer=layer,
        mode=mode,
    )
    
    return str(output_path)
