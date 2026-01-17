"""Green-Book tree estimation - Python implementation of modGBtree.R"""

import pandas as pd
import numpy as np
from typing import Optional, Union, List, Dict, Any
import warnings

from fiesta.utils import (
    check_dataframe,
    check_column_exists,
    calculate_sampling_error,
    EstimationError,
)


def gb_tree_estimates(
    tree_df: pd.DataFrame,
    cond_df: pd.DataFrame,
    pltassgn_df: pd.DataFrame,
    estvar: str = "VOLCFNET",
    estvar_filter: Optional[str] = None,
    estvar_derive: Optional[Dict[str, str]] = None,
    tpa_var: str = "TPA_UNADJ",
    landarea: str = "FOREST",
    woodland: str = "N",
    rowvar: Optional[str] = None,
    colvar: Optional[str] = None,
    pcfilter: Optional[str] = None,
    sumunits: bool = False,
    confidence_level: float = 0.68,
) -> Dict[str, Any]:
    """
    Generate tree estimates using Green-Book estimators.
    
    This implements the non-ratio estimator for estimating tree attributes
    by stratum and domain. Tree attributes are adjusted to per-acre values,
    summed by plot, adjusted for nonsampled conditions, and averaged by stratum.
    
    Args:
        tree_df: Tree table with columns:
            - PLT_CN: Plot unique identifier
            - CONDID: Condition ID
            - TPA_UNADJ: Unadjusted trees per acre
            - estvar: Estimate variable (e.g., VOLCFNET, DRYBIO_AG)
        cond_df: Condition table
        pltassgn_df: Plot assignment table
        estvar: Variable to estimate (e.g., 'VOLCFNET', 'DRYBIO_AG', 'TPA_UNADJ')
        estvar_filter: Optional filter for estimate variable (e.g., 'STATUSCD == 1')
        estvar_derive: Optional derived variable definition
            Example: {'SDI': 'SUM((DIA/10)**1.605 * TPA_UNADJ)'}
        tpa_var: Trees per acre variable name
        landarea: Land area filter ('ALL', 'FOREST', 'TIMBERLAND')
        woodland: Include woodland species ('Y', 'N', 'only')
        rowvar: Row domain variable (e.g., 'SPCD', 'DIA_CLASS')
        colvar: Column domain variable
        pcfilter: Additional plot/condition filter
        sumunits: If True, sum across estimation units
        confidence_level: Confidence level for sampling errors
        
    Returns:
        Dictionary with:
            - 'est': DataFrame with tree estimates
            - 'pse': DataFrame with percent sampling errors
            - 'raw': Dictionary with processing data
            
    Examples:
        >>> # Estimate total volume by species
        >>> result = gb_tree_estimates(
        ...     tree_df=trees,
        ...     cond_df=conditions,
        ...     pltassgn_df=plots,
        ...     estvar='VOLCFNET',
        ...     rowvar='SPCD'
        ... )
        
        >>> # Estimate live tree count by diameter class
        >>> result = gb_tree_estimates(
        ...     tree_df=trees,
        ...     cond_df=conditions,
        ...     pltassgn_df=plots,
        ...     estvar='TPA_UNADJ',
        ...     estvar_filter='STATUSCD == 1',
        ...     rowvar='DIA_CLASS'
        ... )
    """
    # Validate inputs
    tree_df = check_dataframe(tree_df, "tree_df")
    cond_df = check_dataframe(cond_df, "cond_df")
    pltassgn_df = check_dataframe(pltassgn_df, "pltassgn_df")
    
    # Check required columns
    required_tree_cols = ['PLT_CN', tpa_var]
    if estvar and estvar != 'TPA_UNADJ':
        required_tree_cols.append(estvar)
    check_column_exists(tree_df, required_tree_cols, "tree_df")
    
    # Make copies
    trees = tree_df.copy()
    cond = cond_df.copy()
    pltassgn = pltassgn_df.copy()
    
    # Apply land area filter to conditions
    if landarea == "FOREST":
        cond = cond[cond['COND_STATUS_CD'] == 1].copy()
    elif landarea == "TIMBERLAND":
        if 'SITECLCD' in cond.columns and 'RESERVCD' in cond.columns:
            cond = cond[
                (cond['COND_STATUS_CD'] == 1) &
                (cond['SITECLCD'].isin([1, 2, 3, 4, 5, 6])) &
                (cond['RESERVCD'] == 0)
            ].copy()
    
    # Filter woodland species if specified
    if woodland != 'Y' and 'WOODLAND' in trees.columns:
        if woodland == 'N':
            trees = trees[trees['WOODLAND'] == 'N'].copy()
        elif woodland == 'only':
            trees = trees[trees['WOODLAND'] == 'Y'].copy()
    
    # Apply estimate variable filter
    if estvar_filter:
        try:
            trees = trees.query(estvar_filter)
        except Exception as e:
            raise EstimationError(f"Error applying estvar_filter: {e}")
    
    # Calculate per-acre estimate variable
    if estvar_derive:
        # Handle derived variables
        var_name = list(estvar_derive.keys())[0]
        var_expr = estvar_derive[var_name]
        # Simplified - would need full expression parser
        warnings.warn("estvar_derive is simplified in this implementation")
        trees[var_name] = trees.eval(var_expr) if 'eval' in dir(trees) else 0
        estvar = var_name
    
    # Calculate per-acre values
    if estvar == 'TPA_UNADJ':
        trees['EST_ACRE'] = trees[tpa_var]
    else:
        check_column_exists(trees, [estvar], "tree_df")
        trees['EST_ACRE'] = trees[estvar] * trees[tpa_var]
    
    # Merge with conditions to get condition proportions
    trees = pd.merge(
        trees,
        cond[['PLT_CN', 'CONDID', 'CONDPROP_UNADJ']],
        on=['PLT_CN', 'CONDID'],
        how='inner'
    )
    
    # Sum by plot
    plot_sums = trees.groupby('PLT_CN').agg({
        'EST_ACRE': 'sum',
        'CONDPROP_UNADJ': 'first'  # Get any condition prop for adj factor
    }).reset_index()
    
    # Merge with plot assignment
    plot_data = pd.merge(
        plot_sums,
        pltassgn,
        left_on='PLT_CN',
        right_on='CN',
        how='inner'
    )
    
    # Calculate adjustment factor (simplified)
    cond_prop_sum = cond.groupby('PLT_CN')['CONDPROP_UNADJ'].sum().reset_index()
    cond_prop_sum.columns = ['PLT_CN', 'CONDPROP_SUM']
    
    plot_data = pd.merge(plot_data, cond_prop_sum, on='PLT_CN', how='left')
    plot_data['ADJ_FACTOR'] = 1.0 / plot_data['CONDPROP_SUM'].fillna(1.0)
    
    # Adjusted estimate
    plot_data['EST_ACRE_ADJ'] = plot_data['EST_ACRE'] * plot_data['ADJ_FACTOR']
    
    # Calculate stratum-level estimates
    if 'STRATUMCD' in plot_data.columns:
        strata_var = 'STRATUMCD'
    else:
        strata_var = 'STATECD'
    
    # Merge tree data with plot data for domain variables
    if rowvar or colvar:
        # Need to aggregate by domain
        domain_vars = []
        if rowvar:
            domain_vars.append(rowvar)
        if colvar:
            domain_vars.append(colvar)
        
        # Merge trees with plot data to get domains
        tree_plot = pd.merge(
            trees[['PLT_CN'] + domain_vars + ['EST_ACRE']],
            plot_data[['PLT_CN', strata_var, 'ADJ_FACTOR']],
            on='PLT_CN'
        )
        
        tree_plot['EST_ACRE_ADJ'] = tree_plot['EST_ACRE'] * tree_plot['ADJ_FACTOR']
        
        # Aggregate by domain and stratum
        group_vars = domain_vars + [strata_var]
        stratum_est = tree_plot.groupby(group_vars).agg({
            'EST_ACRE_ADJ': ['mean', 'var', 'count']
        }).reset_index()
        stratum_est.columns = group_vars + ['mean_est', 'var_est', 'n_plots']
    else:
        # Overall estimate by stratum
        stratum_est = plot_data.groupby(strata_var).agg({
            'EST_ACRE_ADJ': ['mean', 'var', 'count']
        }).reset_index()
        stratum_est.columns = [strata_var, 'mean_est', 'var_est', 'n_plots']
    
    # Calculate weighted estimates (simplified - would need unit areas)
    total_area = 1000000  # Example area
    stratum_weight = 1.0 / stratum_est[strata_var].nunique()  # Equal weights
    
    if rowvar or colvar:
        est_df = stratum_est.groupby(domain_vars).agg({
            'mean_est': lambda x: (x * stratum_weight).sum() * total_area,
            'var_est': lambda x: (x * stratum_weight**2).sum() * total_area**2,
            'n_plots': 'sum'
        }).reset_index()
        est_df.columns = domain_vars + ['ESTIMATE', 'VARIANCE', 'N_PLOTS']
    else:
        total_est = (stratum_est['mean_est'] * stratum_weight).sum() * total_area
        total_var = (stratum_est['var_est'] * stratum_weight**2).sum() * total_area**2
        est_df = pd.DataFrame({
            'ESTIMATE': [total_est],
            'VARIANCE': [total_var],
            'N_PLOTS': [stratum_est['n_plots'].sum()]
        })
    
    # Calculate percent sampling error
    est_df['PSE'] = calculate_sampling_error(
        est_df['VARIANCE'].values,
        est_df['ESTIMATE'].values,
        confidence_level
    )
    
    # Prepare output
    if rowvar or colvar:
        pse_df = est_df[domain_vars + ['PSE']].copy()
    else:
        pse_df = est_df[['PSE']].copy()
    
    result = {
        'est': est_df,
        'pse': pse_df,
        'raw': {
            'stratum_estimates': stratum_est,
            'n_plots_total': plot_data['PLT_CN'].nunique(),
            'n_trees': len(trees),
        }
    }
    
    return result
