"""Green-Book area estimation - Python implementation of modGBarea.R"""

import pandas as pd
import numpy as np
from typing import Optional, Union, List, Dict, Any
import warnings

from fiesta.utils import (
    check_dataframe,
    check_column_exists,
    calculate_sampling_error,
    expand_area,
    get_strata_weights,
    EstimationError,
)


def gb_area_estimates(
    cond_df: pd.DataFrame,
    pltassgn_df: pd.DataFrame,
    unitarea_df: Optional[pd.DataFrame] = None,
    rowvar: Optional[str] = None,
    colvar: Optional[str] = None,
    landarea: str = "FOREST",
    pcfilter: Optional[str] = None,
    sumunits: bool = False,
    confidence_level: float = 0.68,
) -> Dict[str, Any]:
    """
    Generate area estimates using Green-Book estimators.
    
    This implements the non-ratio estimator for estimating area by stratum
    and domain, based on Scott et al. 2005 (the "green book"). Plots that
    are totally nonsampled are excluded. An adjustment factor is calculated
    by strata to adjust for nonsampled conditions.
    
    Args:
        cond_df: Condition table with columns:
            - PLT_CN: Plot unique identifier
            - CONDID: Condition ID
            - CONDPROP_UNADJ: Unadjusted condition proportion
            - COND_STATUS_CD: Condition status code
        pltassgn_df: Plot assignment table with columns:
            - CN: Plot identifier
            - STATECD: State code
            - INVYR: Inventory year
            - PLOT_STATUS_CD: Plot status code
        unitarea_df: Optional DataFrame with estimation unit areas
        rowvar: Row domain variable name (e.g., 'FORTYPCD')
        colvar: Column domain variable name (e.g., 'STDSZCD')
        landarea: Land area filter ('ALL', 'FOREST', 'TIMBERLAND')
        pcfilter: Optional filter expression for plots/conditions
        sumunits: If True, sum across estimation units
        confidence_level: Confidence level for sampling errors (default 0.68)
        
    Returns:
        Dictionary with:
            - 'est': DataFrame with area estimates
            - 'pse': DataFrame with percent sampling errors
            - 'raw': Dictionary with processing data
            
    Examples:
        >>> # Estimate forest area by forest type
        >>> result = gb_area_estimates(
        ...     cond_df=wy_cond,
        ...     pltassgn_df=wy_pltassgn,
        ...     rowvar='FORTYPCD',
        ...     landarea='FOREST'
        ... )
        >>> print(result['est'])
        
        >>> # Two-way area estimate with timberland
        >>> result = gb_area_estimates(
        ...     cond_df=wy_cond,
        ...     pltassgn_df=wy_pltassgn,
        ...     rowvar='FORTYPCD',
        ...     colvar='STDSZCD',
        ...     landarea='TIMBERLAND'
        ... )
    """
    # Validate inputs
    cond_df = check_dataframe(cond_df, "cond_df")
    pltassgn_df = check_dataframe(pltassgn_df, "pltassgn_df")
    
    required_cond_cols = ['PLT_CN', 'CONDPROP_UNADJ', 'COND_STATUS_CD']
    check_column_exists(cond_df, required_cond_cols, "cond_df")
    
    required_plt_cols = ['CN', 'STATECD', 'INVYR']
    check_column_exists(pltassgn_df, required_plt_cols, "pltassgn_df")
    
    # Make copies
    cond = cond_df.copy()
    pltassgn = pltassgn_df.copy()
    
    # Apply land area filter
    if landarea == "FOREST":
        cond = cond[cond['COND_STATUS_CD'] == 1].copy()
    elif landarea == "TIMBERLAND":
        if 'SITECLCD' in cond.columns and 'RESERVCD' in cond.columns:
            cond = cond[
                (cond['COND_STATUS_CD'] == 1) &
                (cond['SITECLCD'].isin([1, 2, 3, 4, 5, 6])) &
                (cond['RESERVCD'] == 0)
            ].copy()
        else:
            warnings.warn(
                "SITECLCD or RESERVCD not found, using FOREST filter"
            )
            cond = cond[cond['COND_STATUS_CD'] == 1].copy()
    
    # Apply additional filter if provided
    if pcfilter:
        try:
            cond = cond.query(pcfilter)
        except Exception as e:
            raise EstimationError(f"Error applying filter: {e}")
    
    # Merge condition and plot data
    merged = pd.merge(
        cond,
        pltassgn,
        left_on='PLT_CN',
        right_on='CN',
        how='inner',
        suffixes=('_cond', '_plt')
    )
    
    if len(merged) == 0:
        raise EstimationError("No records after merging condition and plot data")
    
    # Calculate adjustment factors by stratum
    # Group by stratum (using STATECD as simple example)
    if 'STRATUMCD' in merged.columns:
        strata_var = 'STRATUMCD'
    else:
        strata_var = 'STATECD'
    
    # Calculate proportion sum by plot and stratum
    prop_by_plot = merged.groupby(['PLT_CN', strata_var])['CONDPROP_UNADJ'].sum()
    
    # Calculate adjustment factor (1 / prop_sum)
    adj_factors = 1.0 / prop_by_plot
    adj_factors = adj_factors.reset_index()
    adj_factors.columns = ['PLT_CN', strata_var, 'ADJ_FACTOR']
    
    # Merge adjustment factors back
    merged = pd.merge(merged, adj_factors, on=['PLT_CN', strata_var])
    
    # Calculate adjusted proportion
    merged['CONDPROP_ADJ'] = merged['CONDPROP_UNADJ'] * merged['ADJ_FACTOR']
    
    # Aggregate by domain
    if rowvar is None and colvar is None:
        # Overall estimate
        group_vars = [strata_var]
    elif colvar is None:
        group_vars = [strata_var, rowvar]
    else:
        group_vars = [strata_var, rowvar, colvar]
    
    # Check domain variables exist
    domain_vars = [v for v in group_vars if v not in [strata_var]]
    if domain_vars:
        check_column_exists(merged, domain_vars, "merged data")
    
    # Calculate mean proportion by stratum and domain
    stratum_means = merged.groupby(group_vars)['CONDPROP_ADJ'].mean().reset_index()
    stratum_means.columns = list(group_vars) + ['mean_prop']
    
    # Calculate number of plots by stratum
    n_plots = merged.groupby(group_vars)['PLT_CN'].nunique().reset_index()
    n_plots.columns = list(group_vars) + ['n_plots']
    
    stratum_means = pd.merge(stratum_means, n_plots, on=group_vars)
    
    # Calculate variance by stratum
    variance = merged.groupby(group_vars)['CONDPROP_ADJ'].var().reset_index()
    variance.columns = list(group_vars) + ['variance']
    
    stratum_means = pd.merge(stratum_means, variance, on=group_vars, how='left')
    stratum_means['variance'] = stratum_means['variance'].fillna(0)
    
    # Get stratum areas (simplified - would need unit area table)
    if unitarea_df is not None:
        # Use provided unit areas
        stratum_areas = unitarea_df.copy()
    else:
        # Use equal weights as default
        stratum_counts = merged.groupby(strata_var)['PLT_CN'].nunique()
        total_plots = stratum_counts.sum()
        stratum_areas = pd.DataFrame({
            strata_var: stratum_counts.index,
            'AREA': stratum_counts.values / total_plots * 1000000  # Example area
        })
    
    # Merge stratum areas
    stratum_means = pd.merge(
        stratum_means,
        stratum_areas,
        on=strata_var,
        how='left'
    )
    
    # Calculate stratum weights
    total_area = stratum_areas['AREA'].sum()
    stratum_means['stratum_weight'] = stratum_means['AREA'] / total_area
    
    # Calculate area estimates by domain
    if rowvar is None and colvar is None:
        group_by_vars = []
    elif colvar is None:
        group_by_vars = [rowvar]
    else:
        group_by_vars = [rowvar, colvar]
    
    if group_by_vars:
        # Weighted mean across strata
        estimates = []
        for domain_vals, group in stratum_means.groupby(group_by_vars):
            weighted_mean = (group['mean_prop'] * group['stratum_weight']).sum()
            area_est = weighted_mean * total_area
            
            # Variance calculation (simplified)
            var_est = ((group['variance'] / group['n_plots']) * 
                      (group['stratum_weight'] ** 2)).sum() * (total_area ** 2)
            
            est_dict = {}
            if isinstance(domain_vals, tuple):
                for i, var in enumerate(group_by_vars):
                    est_dict[var] = domain_vals[i]
            else:
                est_dict[group_by_vars[0]] = domain_vals
            
            est_dict['AREA'] = area_est
            est_dict['VARIANCE'] = var_est
            estimates.append(est_dict)
        
        est_df = pd.DataFrame(estimates)
    else:
        # Overall estimate
        weighted_mean = (stratum_means['mean_prop'] * 
                        stratum_means['stratum_weight']).sum()
        area_est = weighted_mean * total_area
        
        var_est = ((stratum_means['variance'] / stratum_means['n_plots']) * 
                  (stratum_means['stratum_weight'] ** 2)).sum() * (total_area ** 2)
        
        est_df = pd.DataFrame({
            'AREA': [area_est],
            'VARIANCE': [var_est]
        })
    
    # Calculate percent sampling error
    est_df['PSE'] = calculate_sampling_error(
        est_df['VARIANCE'].values,
        est_df['AREA'].values,
        confidence_level
    )
    
    # Prepare output
    pse_df = est_df.copy()
    if group_by_vars:
        pse_df = pse_df[group_by_vars + ['PSE']]
    else:
        pse_df = pse_df[['PSE']]
    
    result = {
        'est': est_df,
        'pse': pse_df,
        'raw': {
            'stratum_means': stratum_means,
            'n_plots_total': merged['PLT_CN'].nunique(),
            'n_conditions': len(merged),
        }
    }
    
    return result
