"""Spatial data import functions - Python implementation of spImportSpatial.R"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
from typing import Optional, Union
import warnings

from fiesta.utils import DataValidationError


def import_spatial(
    layer: Union[str, Path, pd.DataFrame],
    dsn: Optional[Union[str, Path]] = None,
    sql: Optional[str] = None,
    driver: Optional[str] = None,
    polyfix: bool = False,
    verbose: bool = True,
) -> gpd.GeoDataFrame:
    """
    Import a spatial vector layer to a GeoDataFrame.
    
    This function is a Python implementation of spImportSpatial from FIESTA,
    using geopandas instead of R's sf package.
    
    Args:
        layer: Path to spatial file or layer name. Supported formats include:
            - Shapefile (.shp)
            - GeoPackage (.gpkg)
            - GeoJSON (.geojson)
            - File geodatabase layers
            - PostGIS database layer
        dsn: Data source name (directory for shapefiles, database connection, etc.)
        sql: SQL query to filter features during import
        driver: Specific GDAL driver to use (usually auto-detected)
        polyfix: If True, apply buffer(0) to fix invalid geometries
        verbose: If True, print information messages
        
    Returns:
        GeoDataFrame with spatial features
        
    Raises:
        DataValidationError: If layer cannot be imported
        
    Examples:
        >>> # Import shapefile
        >>> boundary = import_spatial("boundary.shp")
        
        >>> # Import from geodatabase
        >>> plots = import_spatial(
        ...     layer="plots",
        ...     dsn="fia_data.gdb"
        ... )
        
        >>> # Import with SQL filter
        >>> forests = import_spatial(
        ...     "stands.shp",
        ...     sql="SELECT * FROM stands WHERE FORTYPCD > 100"
        ... )
        
        >>> # Import and fix invalid geometries
        >>> polys = import_spatial(
        ...     "complex_polys.shp",
        ...     polyfix=True
        ... )
    """
    # Handle DataFrame input (convert to GeoDataFrame)
    if isinstance(layer, pd.DataFrame):
        if 'geometry' not in layer.columns:
            raise DataValidationError(
                "DataFrame must have a 'geometry' column to convert to spatial"
            )
        return gpd.GeoDataFrame(layer, geometry='geometry')
    
    # Construct full path
    if dsn is not None:
        dsn_path = Path(dsn)
        layer_path = dsn_path / layer
    else:
        layer_path = Path(layer)
    
    # Check if file exists (for file-based sources)
    if not str(layer_path).startswith(('http://', 'https://', 'postgresql://')):
        # File-based source
        if not layer_path.exists():
            # Try as just layer name
            layer_path = Path(layer)
            if not layer_path.exists():
                raise DataValidationError(
                    f"Spatial layer not found: {layer}"
                )
    
    # Import spatial data
    try:
        if sql is not None:
            # Use SQL filter
            gdf = gpd.read_file(
                layer_path,
                sql=sql,
                driver=driver,
            )
        else:
            gdf = gpd.read_file(
                layer_path,
                driver=driver,
            )
        
        if verbose:
            print(f"Imported {len(gdf)} features from {layer_path}")
            print(f"CRS: {gdf.crs}")
            print(f"Geometry type: {gdf.geometry.type.unique()}")
    
    except Exception as e:
        raise DataValidationError(
            f"Failed to import spatial layer '{layer}': {e}"
        )
    
    # Check for empty result
    if len(gdf) == 0:
        warnings.warn("Imported spatial layer is empty")
    
    # Fix invalid geometries if requested
    if polyfix and not gdf.empty:
        if verbose:
            print("Applying geometry fixes...")
        
        # Check for invalid geometries
        invalid_mask = ~gdf.geometry.is_valid
        n_invalid = invalid_mask.sum()
        
        if n_invalid > 0:
            if verbose:
                print(f"Found {n_invalid} invalid geometries, applying buffer(0) fix")
            
            # Apply buffer(0) to fix invalid geometries
            gdf.loc[invalid_mask, 'geometry'] = gdf.loc[invalid_mask, 'geometry'].buffer(0)
            
            # Check if fix worked
            still_invalid = ~gdf.geometry.is_valid
            if still_invalid.sum() > 0:
                warnings.warn(
                    f"{still_invalid.sum()} geometries are still invalid after fix"
                )
    
    return gdf


def make_spatial_points(
    df: pd.DataFrame,
    x_col: str = "LON",
    y_col: str = "LAT",
    crs: Union[str, int] = "EPSG:4326",
) -> gpd.GeoDataFrame:
    """
    Convert DataFrame with coordinates to GeoDataFrame with point geometries.
    
    Args:
        df: DataFrame with coordinate columns
        x_col: Column name for x-coordinates (longitude)
        y_col: Column name for y-coordinates (latitude)
        crs: Coordinate reference system (default WGS84)
        
    Returns:
        GeoDataFrame with point geometries
        
    Examples:
        >>> # Create spatial points from FIA plot coordinates
        >>> plots_gdf = make_spatial_points(
        ...     plots_df,
        ...     x_col='LON',
        ...     y_col='LAT',
        ...     crs='EPSG:4326'
        ... )
    """
    if x_col not in df.columns or y_col not in df.columns:
        raise DataValidationError(
            f"Columns '{x_col}' and '{y_col}' must exist in DataFrame"
        )
    
    # Remove rows with missing coordinates
    valid_coords = df[[x_col, y_col]].notna().all(axis=1)
    if not valid_coords.all():
        n_missing = (~valid_coords).sum()
        warnings.warn(f"Removing {n_missing} rows with missing coordinates")
        df = df[valid_coords].copy()
    
    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[x_col], df[y_col]),
        crs=crs,
    )
    
    return gdf


def read_spatial_from_db(
    connection_string: str,
    table_name: str,
    geometry_col: str = "geom",
    sql_filter: Optional[str] = None,
) -> gpd.GeoDataFrame:
    """
    Read spatial data from PostGIS or other spatial database.
    
    Args:
        connection_string: Database connection string
        table_name: Name of the table to read
        geometry_col: Name of the geometry column
        sql_filter: Optional WHERE clause for filtering
        
    Returns:
        GeoDataFrame with spatial data
        
    Examples:
        >>> # Read from PostGIS
        >>> plots = read_spatial_from_db(
        ...     "postgresql://user:password@localhost:5432/fia_db",
        ...     "plots",
        ...     sql_filter="state_cd = 56"
        ... )
    """
    if sql_filter:
        sql = f"SELECT * FROM {table_name} WHERE {sql_filter}"
    else:
        sql = f"SELECT * FROM {table_name}"
    
    try:
        gdf = gpd.read_postgis(
            sql,
            connection_string,
            geom_col=geometry_col,
        )
    except Exception as e:
        raise DataValidationError(
            f"Failed to read from database: {e}"
        )
    
    return gdf
