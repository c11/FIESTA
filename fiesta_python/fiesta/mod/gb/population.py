"""Green-Book population data preparation - Python implementation of modGBpop.R"""

import pandas as pd
import numpy as np
from typing import Optional, Union, List, Dict, Any
from pathlib import Path
import warnings

from fiesta.utils import (
    check_dataframe,
    check_column_exists,
    DataValidationError,
)


def gb_population(
    cond_df: pd.DataFrame,
    plt_df: Optional[pd.DataFrame] = None,
    tree_df: Optional[pd.DataFrame] = None,
    seed_df: Optional[pd.DataFrame] = None,
    pltassgn_df: Optional[pd.DataFrame] = None,
    unitarea_df: Optional[pd.DataFrame] = None,
    stratalut_df: Optional[pd.DataFrame] = None,
    pop_type: str = "CURR",
    areawt: str = "CONDPROP_UNADJ",
    adj: str = "samp",
    unitvar: Optional[str] = None,
    strvar: str = "STRATUMCD",
    strata: bool = False,
) -> Dict[str, Any]:
    """
    Generate population data for Green-Book module estimation.
    
    This function prepares all necessary data for Green-Book estimates,
    including calculating adjustment factors for nonsampled conditions
    and organizing data by estimation units and strata.
    
    Args:
        cond_df: Condition-level data with:
            - PLT_CN: Plot unique identifier
            - CONDID: Condition identifier
            - CONDPROP_UNADJ: Unadjusted condition proportion
            - COND_STATUS_CD: Condition status code
        plt_df: Optional plot-level data
        tree_df: Optional tree-level data
        seed_df: Optional seedling data
        pltassgn_df: Plot assignment to estimation units/strata
        unitarea_df: Area by estimation unit
        stratalut_df: Strata look-up table with weights
        pop_type: Population type ('ALL', 'CURR', 'VOL', 'LULC')
            - ALL: All plots including nonsampled
            - CURR: Current inventory, excluding nonsampled
            - VOL: Volume/tree estimates, excluding nonsampled
            - LULC: Land use change, only plots with previous measurements
        areawt: Variable name for area weights (default: CONDPROP_UNADJ)
        adj: Adjustment method ('samp' for stratum-level, 'plot' for plot-level)
        unitvar: Estimation unit variable name
        strvar: Stratum variable name
        strata: If True, include stratification information
        
    Returns:
        Dictionary with population data:
            - 'condx': Adjusted condition data
            - 'treex': Adjusted tree data (if provided)
            - 'seedx': Adjusted seedling data (if provided)
            - 'pltx': Plot data
            - 'pltassgn': Plot assignments
            - 'unitarea': Area by unit
            - 'stratalut': Strata information
            - 'adj_factors': Adjustment factors
            
    Examples:
        >>> # Prepare population for area estimates
        >>> popdat = gb_population(
        ...     cond_df=conditions,
        ...     pltassgn_df=plot_assignments,
        ...     pop_type='CURR'
        ... )
        
        >>> # Prepare population for tree estimates
        >>> popdat = gb_population(
        ...     cond_df=conditions,
        ...     tree_df=trees,
        ...     pltassgn_df=plot_assignments,
        ...     pop_type='VOL',
        ...     strata=True
        ... )
    """
    # Validate inputs
    cond_df = check_dataframe(cond_df, "cond_df")
    
    required_cond_cols = ['PLT_CN', 'CONDID', areawt, 'COND_STATUS_CD']
    check_column_exists(cond_df, required_cond_cols, "cond_df")
    
    # Make copies
    cond = cond_df.copy()
    
    # Filter by population type
    if pop_type == "CURR" or pop_type == "VOL":
        # Exclude nonsampled plots
        if plt_df is not None and 'PLOT_STATUS_CD' in plt_df.columns:
            sampled_plots = plt_df[plt_df['PLOT_STATUS_CD'] == 1]['CN'].values
            cond = cond[cond['PLT_CN'].isin(sampled_plots)]
    
    # Merge with plot assignment if provided
    if pltassgn_df is not None:
        pltassgn_df = check_dataframe(pltassgn_df, "pltassgn_df")
        
        cond = pd.merge(
            cond,
            pltassgn_df,
            left_on='PLT_CN',
            right_on='CN',
            how='inner',
            suffixes=('', '_plt')
        )
    
    # Calculate adjustment factors
    if adj == "plot":
        # Plot-level adjustments
        plot_prop_sum = cond.groupby('PLT_CN')[areawt].sum().reset_index()
        plot_prop_sum.columns = ['PLT_CN', 'PROP_SUM']
        plot_prop_sum['ADJ_FACTOR'] = 1.0 / plot_prop_sum['PROP_SUM']
        
        cond = pd.merge(cond, plot_prop_sum[['PLT_CN', 'ADJ_FACTOR']], on='PLT_CN')
        
    elif adj == "samp" and strata and strvar in cond.columns:
        # Stratum-level adjustments
        strata_prop_sum = cond.groupby([strvar, 'PLT_CN'])[areawt].sum().reset_index()
        strata_means = strata_prop_sum.groupby(strvar)[areawt].mean().reset_index()
        strata_means.columns = [strvar, 'PROP_MEAN']
        strata_means['ADJ_FACTOR'] = 1.0 / strata_means['PROP_MEAN']
        
        cond = pd.merge(cond, strata_means[[strvar, 'ADJ_FACTOR']], on=strvar, how='left')
    else:
        # No adjustment or simple adjustment
        cond['ADJ_FACTOR'] = 1.0
    
    # Calculate adjusted area weights
    cond[f'{areawt}_ADJ'] = cond[areawt] * cond['ADJ_FACTOR']
    
    # Process tree data if provided
    treex = None
    if tree_df is not None:
        tree_df = check_dataframe(tree_df, "tree_df")
        treex = tree_df.copy()
        
        # Merge with condition adjustments
        treex = pd.merge(
            treex,
            cond[['PLT_CN', 'CONDID', 'ADJ_FACTOR']],
            on=['PLT_CN', 'CONDID'],
            how='inner'
        )
        
        # Calculate adjusted TPA if exists
        if 'TPA_UNADJ' in treex.columns:
            treex['TPA_ADJ'] = treex['TPA_UNADJ'] * treex['ADJ_FACTOR']
    
    # Process seedling data if provided
    seedx = None
    if seed_df is not None:
        seed_df = check_dataframe(seed_df, "seed_df")
        seedx = seed_df.copy()
        
        # Merge with condition adjustments
        seedx = pd.merge(
            seedx,
            cond[['PLT_CN', 'CONDID', 'ADJ_FACTOR']],
            on=['PLT_CN', 'CONDID'],
            how='inner'
        )
    
    # Process strata information
    stratalut = None
    if strata and stratalut_df is not None:
        stratalut_df = check_dataframe(stratalut_df, "stratalut_df")
        stratalut = stratalut_df.copy()
        
        # Calculate strata weights if not provided
        if 'STRWT' not in stratalut.columns:
            if 'PIXELS' in stratalut.columns:
                total_pixels = stratalut['PIXELS'].sum()
                stratalut['STRWT'] = stratalut['PIXELS'] / total_pixels
            elif 'AREA' in stratalut.columns:
                total_area = stratalut['AREA'].sum()
                stratalut['STRWT'] = stratalut['AREA'] / total_area
            else:
                # Equal weights
                n_strata = len(stratalut)
                stratalut['STRWT'] = 1.0 / n_strata
        
        # Add plot counts by stratum
        if strvar in cond.columns:
            plot_counts = cond.groupby(strvar)['PLT_CN'].nunique().reset_index()
            plot_counts.columns = [strvar, 'N_PLOTS']
            stratalut = pd.merge(stratalut, plot_counts, on=strvar, how='left')
            stratalut['N_PLOTS'] = stratalut['N_PLOTS'].fillna(0)
    
    # Build result dictionary
    result = {
        'condx': cond,
        'cuniqueid': 'PLT_CN',
        'condid': 'CONDID',
        'areawt': areawt,
        'areawt_adj': f'{areawt}_ADJ',
    }
    
    if treex is not None:
        result['treex'] = treex
        result['tuniqueid'] = 'PLT_CN'
    
    if seedx is not None:
        result['seedx'] = seedx
    
    if plt_df is not None:
        result['pltx'] = plt_df
    
    if pltassgn_df is not None:
        result['pltassgn'] = pltassgn_df
    
    if unitarea_df is not None:
        result['unitarea'] = unitarea_df
        if unitvar:
            result['unitvar'] = unitvar
    
    if stratalut is not None:
        result['stratalut'] = stratalut
        result['strvar'] = strvar
    
    result['pop_type'] = pop_type
    result['adj'] = adj
    
    return result


def prepare_population_simple(
    cond_df: pd.DataFrame,
    pltassgn_df: pd.DataFrame,
    tree_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Simplified population preparation for basic estimates.
    
    Args:
        cond_df: Condition data
        pltassgn_df: Plot assignment data
        tree_df: Optional tree data
        
    Returns:
        Dictionary with prepared population data
    """
    return gb_population(
        cond_df=cond_df,
        tree_df=tree_df,
        pltassgn_df=pltassgn_df,
        pop_type="CURR",
        adj="plot",
        strata=False,
    )
