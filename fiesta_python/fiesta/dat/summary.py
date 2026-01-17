"""Data summary functions for tree and condition data."""

import pandas as pd
import numpy as np
from typing import Optional, Union, List, Dict, Any

from fiesta.utils import check_dataframe, check_column_exists


def summarize_conditions(
    cond_df: pd.DataFrame,
    group_vars: Optional[Union[str, List[str]]] = None,
    area_var: str = "CONDPROP_UNADJ",
    plot_area: float = 1.0,
    status_var: str = "COND_STATUS_CD",
    include_counts: bool = True,
) -> pd.DataFrame:
    """
    Summarize condition-level data.
    
    Args:
        cond_df: Condition DataFrame
        group_vars: Variables to group by (e.g., forest type, size class)
        area_var: Column name for condition proportion
        plot_area: Plot area for expansion
        status_var: Column name for condition status
        include_counts: If True, include plot/condition counts
        
    Returns:
        Summary DataFrame with area estimates
        
    Examples:
        >>> # Summarize area by forest type
        >>> summary = summarize_conditions(
        ...     cond_df,
        ...     group_vars='FORTYPCD',
        ...     area_var='CONDPROP_UNADJ'
        ... )
    """
    cond_df = check_dataframe(cond_df, "cond_df")
    check_column_exists(cond_df, [area_var], "cond_df")
    
    if status_var in cond_df.columns:
        # Filter to sampled forest land (status code 1)
        cond_df = cond_df[cond_df[status_var] == 1].copy()
    
    if group_vars is None:
        # Overall summary
        result = pd.DataFrame({
            'total_area': [cond_df[area_var].sum() * plot_area],
        })
        if include_counts:
            result['n_plots'] = cond_df['PLT_CN'].nunique() if 'PLT_CN' in cond_df.columns else len(cond_df)
            result['n_conditions'] = len(cond_df)
    else:
        if isinstance(group_vars, str):
            group_vars = [group_vars]
        
        check_column_exists(cond_df, group_vars, "cond_df")
        
        # Group and summarize
        result = cond_df.groupby(group_vars).agg({
            area_var: 'sum',
        }).reset_index()
        
        result['area'] = result[area_var] * plot_area
        result = result.drop(columns=[area_var])
        
        if include_counts:
            counts = cond_df.groupby(group_vars).agg({
                'PLT_CN': 'nunique' if 'PLT_CN' in cond_df.columns else 'count',
            }).reset_index()
            counts.columns = list(group_vars) + ['n_plots']
            result = pd.merge(result, counts, on=group_vars)
            
            cond_counts = cond_df.groupby(group_vars).size().reset_index(name='n_conditions')
            result = pd.merge(result, cond_counts, on=group_vars)
    
    return result


def summarize_trees(
    tree_df: pd.DataFrame,
    cond_df: Optional[pd.DataFrame] = None,
    group_vars: Optional[Union[str, List[str]]] = None,
    volume_var: Optional[str] = "VOLCFNET",
    biomass_var: Optional[str] = "DRYBIO_AG",
    tpa_var: str = "TPA_UNADJ",
    status_var: str = "STATUSCD",
    live_status: List[int] = [1],
) -> pd.DataFrame:
    """
    Summarize tree-level data with volume and biomass.
    
    Args:
        tree_df: Tree DataFrame
        cond_df: Optional condition DataFrame for merging
        group_vars: Variables to group by
        volume_var: Column name for volume
        biomass_var: Column name for biomass
        tpa_var: Trees per acre expansion factor
        status_var: Tree status variable
        live_status: List of status codes for live trees
        
    Returns:
        Summary DataFrame with tree statistics
        
    Examples:
        >>> # Summarize by species
        >>> summary = summarize_trees(
        ...     tree_df,
        ...     group_vars='SPCD',
        ...     volume_var='VOLCFNET'
        ... )
    """
    tree_df = check_dataframe(tree_df, "tree_df")
    
    # Filter to live trees if status variable exists
    if status_var in tree_df.columns:
        tree_df = tree_df[tree_df[status_var].isin(live_status)].copy()
    
    # Calculate weighted values
    tree_df = tree_df.copy()
    
    if volume_var and volume_var in tree_df.columns:
        check_column_exists(tree_df, [volume_var, tpa_var], "tree_df")
        tree_df['volume_acre'] = tree_df[volume_var] * tree_df[tpa_var]
    
    if biomass_var and biomass_var in tree_df.columns:
        check_column_exists(tree_df, [biomass_var, tpa_var], "tree_df")
        tree_df['biomass_acre'] = tree_df[biomass_var] * tree_df[tpa_var]
    
    tree_df['tpa'] = tree_df[tpa_var]
    
    # Aggregate
    agg_dict = {'tpa': 'sum'}
    
    if 'volume_acre' in tree_df.columns:
        agg_dict['volume_acre'] = 'sum'
    if 'biomass_acre' in tree_df.columns:
        agg_dict['biomass_acre'] = 'sum'
    
    if group_vars is None:
        # Overall summary
        result = pd.DataFrame(tree_df[list(agg_dict.keys())].sum()).T
        result['n_trees'] = len(tree_df)
    else:
        if isinstance(group_vars, str):
            group_vars = [group_vars]
        
        check_column_exists(tree_df, group_vars, "tree_df")
        
        result = tree_df.groupby(group_vars).agg(agg_dict).reset_index()
        
        # Add counts
        tree_counts = tree_df.groupby(group_vars).size().reset_index(name='n_trees')
        result = pd.merge(result, tree_counts, on=group_vars)
    
    # Merge with condition data if provided
    if cond_df is not None:
        cond_df = check_dataframe(cond_df, "cond_df")
        # Would merge on PLT_CN + CONDID here
        pass
    
    return result


def summarize_tree_domain(
    tree_df: pd.DataFrame,
    domain_var: str,
    volume_var: Optional[str] = "VOLCFNET",
    biomass_var: Optional[str] = "DRYBIO_AG",
    tpa_var: str = "TPA_UNADJ",
    calculate_percentage: bool = True,
) -> pd.DataFrame:
    """
    Summarize trees by domain with percentages.
    
    Args:
        tree_df: Tree DataFrame
        domain_var: Domain variable (e.g., species, diameter class)
        volume_var: Column name for volume
        biomass_var: Column name for biomass
        tpa_var: Trees per acre expansion factor
        calculate_percentage: If True, add percentage columns
        
    Returns:
        Summary DataFrame with domain statistics and percentages
        
    Examples:
        >>> # Summarize by diameter class
        >>> summary = summarize_tree_domain(
        ...     tree_df,
        ...     domain_var='DIA_CLASS',
        ...     volume_var='VOLCFNET'
        ... )
    """
    result = summarize_trees(
        tree_df,
        group_vars=domain_var,
        volume_var=volume_var,
        biomass_var=biomass_var,
        tpa_var=tpa_var,
    )
    
    if calculate_percentage:
        # Calculate percentages
        total_tpa = result['tpa'].sum()
        result['tpa_pct'] = (result['tpa'] / total_tpa * 100) if total_tpa > 0 else 0
        
        if 'volume_acre' in result.columns:
            total_vol = result['volume_acre'].sum()
            result['volume_pct'] = (result['volume_acre'] / total_vol * 100) if total_vol > 0 else 0
        
        if 'biomass_acre' in result.columns:
            total_bio = result['biomass_acre'].sum()
            result['biomass_pct'] = (result['biomass_acre'] / total_bio * 100) if total_bio > 0 else 0
    
    # Sort by percentage or count
    if 'volume_pct' in result.columns:
        result = result.sort_values('volume_pct', ascending=False)
    else:
        result = result.sort_values('tpa', ascending=False)
    
    return result
