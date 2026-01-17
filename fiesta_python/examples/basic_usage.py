"""Example usage of FIESTA-Py package."""

import fiesta
from fiesta.dat import filter_data, frequency_table
from fiesta.sp import import_spatial, extract_raster, clip_poly
from fiesta.mod.gb import gb_area_estimates
import pandas as pd

# =============================================================================
# Example 1: Basic Data Filtering
# =============================================================================

def example_data_filtering():
    """Demonstrate data filtering capabilities."""
    print("=" * 60)
    print("Example 1: Data Filtering")
    print("=" * 60)
    
    # Create example data
    data = pd.DataFrame({
        'PLOT_ID': range(1, 11),
        'FORTYPCD': [182, 184, 201, 221, 221, 184, 221, 182, 182, 201],
        'STDSZCD': [1, 2, 3, 1, 2, 3, 1, 2, 3, 1],
        'INVYR': [2015, 2015, 2016, 2016, 2017, 2017, 2018, 2018, 2019, 2019],
        'AREA': [10, 15, 20, 12, 18, 22, 14, 16, 19, 21]
    })
    
    # Filter by forest type
    result = filter_data(data, xfilter="FORTYPCD == 221")
    print(f"\nOriginal records: {len(data)}")
    print(f"Filtered records (FORTYPCD == 221): {len(result['xf'])}")
    print(result['xf'])
    
    # Filter by multiple conditions
    result = filter_data(data, xfilter="FORTYPCD == 221 and STDSZCD >= 2")
    print(f"\nFiltered records (FORTYPCD == 221 AND STDSZCD >= 2): {len(result['xf'])}")
    print(result['xf'])


# =============================================================================
# Example 2: Frequency Tables
# =============================================================================

def example_frequency_tables():
    """Demonstrate frequency table creation."""
    print("\n" + "=" * 60)
    print("Example 2: Frequency Tables")
    print("=" * 60)
    
    data = pd.DataFrame({
        'FORTYPCD': [182, 184, 201, 221, 221, 184, 221, 182, 182, 201],
        'STDSZCD': [1, 2, 3, 1, 2, 3, 1, 2, 3, 1],
        'AREA': [10, 15, 20, 12, 18, 22, 14, 16, 19, 21]
    })
    
    # Simple frequency
    freq = frequency_table(data, 'FORTYPCD')
    print("\nFrequency by Forest Type:")
    print(freq)
    
    # Weighted frequency
    freq_weighted = frequency_table(data, 'FORTYPCD', weights='AREA', normalize=True)
    print("\nWeighted Frequency (proportions):")
    print(freq_weighted)
    
    # Two-way frequency
    from fiesta.dat import crosstab
    ct = crosstab(data, 'FORTYPCD', 'STDSZCD', values='AREA', aggfunc='sum')
    print("\nCross-tabulation of Forest Type by Size Class:")
    print(ct)


# =============================================================================
# Example 3: Spatial Operations
# =============================================================================

def example_spatial_operations():
    """Demonstrate spatial data operations."""
    print("\n" + "=" * 60)
    print("Example 3: Spatial Operations")
    print("=" * 60)
    
    # Create example point data
    import geopandas as gpd
    from shapely.geometry import Point
    
    points_data = pd.DataFrame({
        'PLOT_ID': [1, 2, 3, 4, 5],
        'LON': [-107.5, -107.4, -107.6, -107.3, -107.7],
        'LAT': [43.0, 43.1, 42.9, 43.2, 42.8],
        'ELEVATION': [2100, 2200, 2000, 2300, 1900]
    })
    
    # Create spatial points
    from fiesta.sp.import_spatial import make_spatial_points
    plots_gdf = make_spatial_points(
        points_data,
        x_col='LON',
        y_col='LAT',
        crs='EPSG:4326'
    )
    
    print(f"\nCreated {len(plots_gdf)} spatial points")
    print(f"CRS: {plots_gdf.crs}")
    print(plots_gdf.head())


# =============================================================================
# Example 4: Area Estimation
# =============================================================================

def example_area_estimation():
    """Demonstrate Green-Book area estimation."""
    print("\n" + "=" * 60)
    print("Example 4: Area Estimation")
    print("=" * 60)
    
    # Create example condition data
    cond_data = pd.DataFrame({
        'PLT_CN': [1, 1, 2, 2, 3, 3, 4, 4, 5, 5],
        'CONDID': [1, 2, 1, 2, 1, 2, 1, 2, 1, 2],
        'CONDPROP_UNADJ': [0.7, 0.3, 0.6, 0.4, 0.8, 0.2, 0.5, 0.5, 0.9, 0.1],
        'COND_STATUS_CD': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        'FORTYPCD': [182, 184, 221, 221, 182, 201, 221, 182, 184, 221],
        'STDSZCD': [1, 2, 1, 2, 1, 3, 2, 1, 2, 1]
    })
    
    # Create example plot assignment data
    pltassgn_data = pd.DataFrame({
        'CN': [1, 2, 3, 4, 5],
        'STATECD': [56, 56, 56, 56, 56],
        'INVYR': [2015, 2015, 2016, 2016, 2017],
        'PLOT_STATUS_CD': [1, 1, 1, 1, 1]
    })
    
    # Calculate area estimates
    result = gb_area_estimates(
        cond_df=cond_data,
        pltassgn_df=pltassgn_data,
        rowvar='FORTYPCD',
        landarea='FOREST'
    )
    
    print("\nArea Estimates by Forest Type:")
    print(result['est'])
    print("\nPercent Sampling Errors:")
    print(result['pse'])


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("FIESTA-Py Example Usage")
    print("=" * 60)
    
    # Run examples
    example_data_filtering()
    example_frequency_tables()
    example_spatial_operations()
    example_area_estimation()
    
    print("\n" + "=" * 60)
    print("Examples completed successfully!")
    print("=" * 60)
