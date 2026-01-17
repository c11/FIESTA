"""Functions for retrieving FIA plot data."""

import pandas as pd
from typing import Optional, List, Union, Dict
from pathlib import Path
import warnings

from fiesta.utils import check_dataframe, DataValidationError


def get_plots(
    states: Optional[Union[str, List[str]]] = None,
    evalid: Optional[Union[str, int]] = None,
    invyrs: Optional[Union[int, List[int]]] = None,
    data_dir: Optional[Union[str, Path]] = None,
    tables: List[str] = ["PLT", "COND", "TREE"],
    returnSpatial: bool = False,
    coords: Optional[List[str]] = None,
    crs: str = "EPSG:4326",
) -> Dict[str, pd.DataFrame]:
    """
    Retrieve FIA plot data from CSV files or database.
    
    Args:
        states: State code(s) or abbreviation(s) (e.g., 'WY' or ['WY', 'MT'])
        evalid: Evaluation identifier
        invyrs: Inventory year(s) to include
        data_dir: Directory containing FIA data files
        tables: List of FIA tables to retrieve ('PLT', 'COND', 'TREE', etc.)
        returnSpatial: If True, return plot table as GeoDataFrame with coordinates
        coords: Column names for coordinates [lon, lat], default ['LON', 'LAT']
        crs: Coordinate reference system for spatial data
        
    Returns:
        Dictionary of DataFrames with requested FIA tables
        
    Examples:
        >>> # Get Wyoming FIA data
        >>> fia_data = get_plots(
        ...     states='WY',
        ...     evalid='561301',
        ...     data_dir='/path/to/fia/data'
        ... )
        >>> plots = fia_data['PLT']
        >>> cond = fia_data['COND']
        >>> tree = fia_data['TREE']
        
        >>> # Get multiple states with spatial data
        >>> fia_data = get_plots(
        ...     states=['WY', 'MT', 'ID'],
        ...     invyrs=[2015, 2016, 2017],
        ...     returnSpatial=True
        ... )
    """
    if states is None and evalid is None:
        raise DataValidationError(
            "Must provide either 'states' or 'evalid' parameter"
        )
    
    if data_dir is None:
        raise DataValidationError(
            "Must provide 'data_dir' parameter pointing to FIA data location"
        )
    
    data_dir = Path(data_dir)
    if not data_dir.exists():
        raise DataValidationError(f"Data directory not found: {data_dir}")
    
    # Ensure states is a list
    if isinstance(states, str):
        states = [states]
    
    # Ensure invyrs is a list if provided
    if invyrs is not None and isinstance(invyrs, int):
        invyrs = [invyrs]
    
    # State code mapping
    state_codes = {
        'WY': 56, 'MT': 30, 'ID': 16, 'CO': 8, 'UT': 49,
        'NM': 35, 'AZ': 4, 'NV': 32, 'CA': 6, 'OR': 41,
        'WA': 53, 'AK': 2, # Add more as needed
    }
    
    result = {}
    
    # Load each requested table
    for table in tables:
        dfs = []
        
        for state in states:
            # Convert state abbreviation to code if needed
            if isinstance(state, str) and state.upper() in state_codes:
                state_cd = state_codes[state.upper()]
                state_abbr = state.upper()
            else:
                state_cd = state
                state_abbr = [k for k, v in state_codes.items() if v == state][0]
            
            # Construct file path (common FIA CSV naming convention)
            file_pattern = f"{state_abbr}_{table}.csv"
            file_path = data_dir / file_pattern
            
            if not file_path.exists():
                # Try alternative patterns
                file_path = data_dir / state_abbr / file_pattern
                if not file_path.exists():
                    warnings.warn(f"File not found: {file_pattern}")
                    continue
            
            try:
                df = pd.read_csv(file_path, low_memory=False)
                
                # Filter by evaluation ID if provided
                if evalid is not None and 'EVALID' in df.columns:
                    df = df[df['EVALID'] == int(evalid)]
                
                # Filter by inventory years if provided
                if invyrs is not None and 'INVYR' in df.columns:
                    df = df[df['INVYR'].isin(invyrs)]
                
                dfs.append(df)
            
            except Exception as e:
                warnings.warn(f"Error loading {file_pattern}: {e}")
                continue
        
        if dfs:
            # Combine data from multiple states
            combined_df = pd.concat(dfs, ignore_index=True)
            result[table] = combined_df
    
    # Convert plot table to spatial if requested
    if returnSpatial and 'PLT' in result:
        from fiesta.sp.import_spatial import make_spatial_points
        
        if coords is None:
            coords = ['LON', 'LAT']
        
        if coords[0] in result['PLT'].columns and coords[1] in result['PLT'].columns:
            result['PLT'] = make_spatial_points(
                result['PLT'],
                x_col=coords[0],
                y_col=coords[1],
                crs=crs,
            )
    
    return result


def get_plot_by_coords(
    lon: float,
    lat: float,
    buffer_miles: float = 10.0,
    data_dir: Optional[Union[str, Path]] = None,
    **kwargs
) -> Dict[str, pd.DataFrame]:
    """
    Get FIA plots within buffer distance of coordinates.
    
    Args:
        lon: Longitude
        lat: Latitude
        buffer_miles: Buffer distance in miles
        data_dir: Directory containing FIA data
        **kwargs: Additional arguments passed to get_plots()
        
    Returns:
        Dictionary of DataFrames with plots within buffer
        
    Examples:
        >>> # Get plots within 10 miles of location
        >>> plots = get_plot_by_coords(
        ...     lon=-107.5,
        ...     lat=43.0,
        ...     buffer_miles=10,
        ...     data_dir='/path/to/fia/data'
        ... )
    """
    from shapely.geometry import Point
    import geopandas as gpd
    
    # Get plots with spatial coordinates
    fia_data = get_plots(
        data_dir=data_dir,
        returnSpatial=True,
        **kwargs
    )
    
    if 'PLT' not in fia_data:
        return {}
    
    plots_gdf = fia_data['PLT']
    
    # Create buffer point
    point = Point(lon, lat)
    point_gdf = gpd.GeoDataFrame(
        {'geometry': [point]},
        crs='EPSG:4326'
    )
    
    # Reproject to suitable projection for distance (UTM)
    from fiesta.sp.reproject import get_utm_crs
    utm_crs = get_utm_crs(lon, lat)
    
    point_utm = point_gdf.to_crs(utm_crs)
    plots_utm = plots_gdf.to_crs(utm_crs)
    
    # Convert miles to meters
    buffer_meters = buffer_miles * 1609.34
    
    # Buffer and select
    buffer_geom = point_utm.geometry.iloc[0].buffer(buffer_meters)
    mask = plots_utm.geometry.within(buffer_geom)
    
    fia_data['PLT'] = plots_gdf[mask]
    
    # Filter other tables by PLT_CN
    if len(fia_data['PLT']) > 0:
        plt_cns = fia_data['PLT']['CN'].values
        
        for table in ['COND', 'TREE', 'SEEDLING']:
            if table in fia_data:
                fia_data[table] = fia_data[table][
                    fia_data[table]['PLT_CN'].isin(plt_cns)
                ]
    
    return fia_data
