"""
FIESTA Estimation Examples

Demonstrates the use of various estimation modules:
- Green-Book (GB): Traditional FIA estimation
- Photo-Based (PB): Photo interpretation estimates
- Model-Assisted (MA): Estimates using auxiliary data
- Small Area (SA): Estimates for small domains
"""

import pandas as pd
import numpy as np

# Import FIESTA estimation modules
from fiesta.mod.gb import (
    gb_area_estimates,
    gb_tree_estimates,
    gb_ratio_estimates,
    calculate_per_acre_ratio,
    gb_population,
)
from fiesta.mod.pb import pb_estimates, pb_ratio_estimates
from fiesta.mod.ma import ma_area_estimates
from fiesta.mod.sa import sa_area_estimates


def create_example_data():
    """Create synthetic example data for demonstrations."""
    
    # Create tree data
    np.random.seed(42)
    n_trees = 1000
    
    tree_df = pd.DataFrame({
        'PLT_CN': np.repeat(range(1, 51), 20),  # 50 plots, 20 trees each
        'TPA_UNADJ': np.random.uniform(5, 50, n_trees),
        'VOLCFNET': np.random.uniform(10, 200, n_trees),
        'DIA': np.random.uniform(5, 30, n_trees),
        'SPCD': np.random.choice([93, 122, 202, 746], n_trees),
        'CONDID': 1,
    })
    
    # Create condition data
    cond_df = pd.DataFrame({
        'PLT_CN': range(1, 51),
        'CONDID': 1,
        'CONDPROP_UNADJ': np.random.uniform(0.8, 1.0, 50),
        'FORTYPCD': np.random.choice([220, 260, 360, 370], 50),
        'COND_STATUS_CD': 1,
    })
    
    # Create plot assignment data
    pltassgn_df = pd.DataFrame({
        'CN': range(1, 51),
        'PLT_CN': range(1, 51),
        'STRATUMCD': np.random.choice([1, 2, 3], 50),
        'COUNTYCD': np.random.choice([1, 2, 3, 4], 50),
        'STATECD': 56,  # Wyoming
    })
    
    # Create unit area data
    unitarea_df = pd.DataFrame({
        'ESTN_UNIT': [1, 2, 3, 4],
        'AREA': [100000, 150000, 120000, 90000],
    })
    
    # Create photo-based point data
    n_points = 500
    pnt_df = pd.DataFrame({
        'PLT_CN': np.repeat(range(1, 51), 10),  # 50 plots, 10 points each
        'POINT_ID': range(1, n_points + 1),
        'cover_1': np.random.choice([1, 2, 3, 4, 999], n_points),
        'DOT_CNT': range(1, n_points + 1),
    })
    
    return tree_df, cond_df, pltassgn_df, unitarea_df, pnt_df


def example_gb_area():
    """Example: Green-Book area estimation."""
    print("\n" + "="*80)
    print("GREEN-BOOK AREA ESTIMATION")
    print("="*80)
    
    tree_df, cond_df, pltassgn_df, unitarea_df, _ = create_example_data()
    
    # Prepare population data
    pop_data = gb_population(
        cond_df=cond_df,
        pltassgn_df=pltassgn_df,
        unitarea_df=unitarea_df
    )
    
    # Calculate area estimates by forest type
    result = gb_area_estimates(
        tree_df=tree_df,
        cond_df=cond_df,
        pltassgn_df=pltassgn_df,
        rowvar='FORTYPCD',
        landarea='FOREST'
    )
    
    print("\nArea estimates by forest type:")
    print(result['est'])
    
    print("\nPercent sampling error:")
    print(result['pse'])
    
    return result


def example_gb_tree():
    """Example: Green-Book tree/volume estimation."""
    print("\n" + "="*80)
    print("GREEN-BOOK TREE/VOLUME ESTIMATION")
    print("="*80)
    
    tree_df, cond_df, pltassgn_df, unitarea_df, _ = create_example_data()
    
    # Calculate volume estimates by species
    result = gb_tree_estimates(
        tree_df=tree_df,
        cond_df=cond_df,
        pltassgn_df=pltassgn_df,
        estvarn='VOLCFNET',
        rowvar='SPCD',
        landarea='FOREST'
    )
    
    print("\nVolume estimates by species:")
    print(result['est'])
    
    print("\nPercent sampling error:")
    print(result['pse'])
    
    return result


def example_gb_ratio():
    """Example: Green-Book ratio estimation."""
    print("\n" + "="*80)
    print("GREEN-BOOK RATIO ESTIMATION")
    print("="*80)
    
    tree_df, cond_df, pltassgn_df, unitarea_df, _ = create_example_data()
    
    # Calculate volume per acre by species
    result = calculate_per_acre_ratio(
        tree_df=tree_df,
        cond_df=cond_df,
        pltassgn_df=pltassgn_df,
        numerator_var='VOLCFNET',
        rowvar='SPCD'
    )
    
    print("\nVolume per acre by species:")
    print(result['est'])
    
    print("\nPercent sampling error:")
    print(result['pse'])
    
    return result


def example_pb_estimates():
    """Example: Photo-based estimation."""
    print("\n" + "="*80)
    print("PHOTO-BASED ESTIMATION")
    print("="*80)
    
    tree_df, cond_df, pltassgn_df, unitarea_df, pnt_df = create_example_data()
    
    # Create plot data for PB
    plt_df = pltassgn_df.copy()
    plt_df['PLOT_ID'] = plt_df['PLT_CN']
    pnt_df['PLOT_ID'] = pnt_df['PLT_CN']
    
    # Calculate percent cover by land cover class
    result = pb_estimates(
        pnt_df=pnt_df,
        plt_df=plt_df,
        unitarea_df=unitarea_df.rename(columns={'ESTN_UNIT': 'COUNTYCD'}),
        tabtype='PCT',
        rowvar='cover_1',
        nonsamp_pntfilter='cover_1 != 999',
        unitvar='COUNTYCD'
    )
    
    print("\nPercent cover by land cover class:")
    print(result['est'])
    
    print("\nPercent sampling error:")
    print(result['pse'])
    
    return result


def example_ma_estimates():
    """Example: Model-assisted estimation."""
    print("\n" + "="*80)
    print("MODEL-ASSISTED ESTIMATION")
    print("="*80)
    
    tree_df, cond_df, pltassgn_df, unitarea_df, _ = create_example_data()
    
    # Create auxiliary data (e.g., from remote sensing)
    auxiliary_df = pd.DataFrame({
        'PLT_CN': range(1, 51),
        'POSTSTRATA': np.random.choice([1, 2, 3], 50),
        'AREA': np.random.uniform(1000, 5000, 50),
        'NDVI': np.random.uniform(0.3, 0.8, 50),
    })
    
    # Calculate post-stratified area estimates
    result = ma_area_estimates(
        tree_df=tree_df,
        cond_df=cond_df,
        pltassgn_df=pltassgn_df,
        auxiliary_df=auxiliary_df,
        modeltype='POSTSTRAT',
        rowvar='FORTYPCD'
    )
    
    print("\nModel-assisted area estimates by forest type:")
    print(result['est'])
    
    print("\nPercent sampling error:")
    print(result['pse'])
    
    return result


def example_sa_estimates():
    """Example: Small area estimation."""
    print("\n" + "="*80)
    print("SMALL AREA ESTIMATION")
    print("="*80)
    
    tree_df, cond_df, pltassgn_df, unitarea_df, _ = create_example_data()
    
    # Calculate estimates for small domains (counties)
    result = sa_area_estimates(
        tree_df=tree_df,
        cond_df=cond_df,
        pltassgn_df=pltassgn_df,
        smalldomain='COUNTYCD',
        method='DIRECT'
    )
    
    print("\nSmall area estimates by county:")
    print(result['est'])
    
    print("\nPercent sampling error:")
    print(result['pse'])
    
    return result


def main():
    """Run all estimation examples."""
    print("\n" + "="*80)
    print("FIESTA ESTIMATION MODULE EXAMPLES")
    print("="*80)
    print("\nThis script demonstrates various estimation methods in FIESTA:")
    print("1. Green-Book (GB) - Traditional FIA estimation")
    print("2. Photo-Based (PB) - Photo interpretation estimates")
    print("3. Model-Assisted (MA) - Estimates using auxiliary data")
    print("4. Small Area (SA) - Estimates for small domains")
    
    try:
        # Run all examples
        example_gb_area()
        example_gb_tree()
        example_gb_ratio()
        example_pb_estimates()
        example_ma_estimates()
        example_sa_estimates()
        
        print("\n" + "="*80)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("="*80)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
