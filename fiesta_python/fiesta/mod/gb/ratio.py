"""Green-Book ratio estimation - Python implementation of modGBratio.R"""

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


def gb_ratio_estimates(
    tree_df: pd.DataFrame,
    cond_df: pd.DataFrame,
    pltassgn_df: pd.DataFrame,
    estvarn: str,
    estvard: str,
    ratio_type: str = "PERACRE",
    estvarn_filter: Optional[str] = None,
    estvard_filter: Optional[str] = None,
    landarea: str = "FOREST",
    rowvar: Optional[str] = None,
    colvar: Optional[str] = None,
    tpa_var: str = "TPA_UNADJ",
    confidence_level: float = 0.68,
) -> Dict[str, Any]:
    """
    Generate ratio estimates using Green-Book ratio-of-means estimator.
    
    Calculates per-acre or per-tree estimates by domain. Uses the ratio-of-means
    (ROM) estimator from Scott et al. 2005 (the green book) chapter 4.
    
    Args:
        tree_df: Tree data
        cond_df: Condition data
        pltassgn_df: Plot assignment data
        estvarn: Numerator estimate variable
        estvard: Denominator estimate variable
        ratio_type: Type of ratio ('PERACRE', 'PERTREE')
        estvarn_filter: Filter for numerator
        estvard_filter: Filter for denominator
        landarea: Land area filter ('ALL', 'FOREST', 'TIMBERLAND')
        rowvar: Row domain variable
        colvar: Column domain variable
        tpa_var: Trees per acre variable
        confidence_level: Confidence level for errors
        
    Returns:
        Dictionary with ratio estimates and sampling errors
        
    Examples:
        >>> # Volume per acre
        >>> result = gb_ratio_estimates(
        ...     tree_df=trees,
        ...     cond_df=conditions,
        ...     pltassgn_df=plots,
        ...     estvarn='VOLCFNET',
        ...     estvard='ACRES',
        ...     ratio_type='PERACRE'
        ... )
        
        >>> # Volume per tree by species
        >>> result = gb_ratio_estimates(
        ...     tree_df=trees,
        ...     cond_df=conditions,
        ...     pltassgn_df=plots,
        ...     estvarn='VOLCFNET',
        ...     estvard='TPA_UNADJ',
        ...     ratio_type='PERTREE',
        ...     rowvar='SPCD'
        ... )
    """
    # Validate inputs
    tree_df = check_dataframe(tree_df, "tree_df")
    cond_df = check_dataframe(cond_df, "cond_df")
    pltassgn_df = check_dataframe(pltassgn_df, "pltassgn_df")
    
    # Make copies
    trees_n = tree_df.copy()
    trees_d = tree_df.copy()
    cond = cond_df.copy()
    
    # Apply filters
    if estvarn_filter:
        trees_n = trees_n.query(estvarn_filter)
    if estvard_filter:
        trees_d = trees_d.query(estvard_filter)
    
    # Calculate per-acre values for numerator
    check_column_exists(trees_n, [estvarn, tpa_var], "tree_df")
    trees_n['NUMER_ACRE'] = trees_n[estvarn] * trees_n[tpa_var]
    
    # Calculate per-acre values for denominator
    if ratio_type == "PERTREE":
        check_column_exists(trees_d, [estvard, tpa_var], "tree_df")
        trees_d['DENOM_ACRE'] = trees_d[estvard] * trees_d[tpa_var]
    else:  # PERACRE
        # Denominator is area
        trees_d['DENOM_ACRE'] = trees_d[tpa_var]
    
    # Sum by plot
    numer_by_plot = trees_n.groupby('PLT_CN')['NUMER_ACRE'].sum().reset_index()
    numer_by_plot.columns = ['PLT_CN', 'NUMER']
    
    denom_by_plot = trees_d.groupby('PLT_CN')['DENOM_ACRE'].sum().reset_index()
    denom_by_plot.columns = ['PLT_CN', 'DENOM']
    
    # Merge numerator and denominator
    plot_data = pd.merge(numer_by_plot, denom_by_plot, on='PLT_CN', how='outer').fillna(0)
    
    # Merge with plot assignments
    plot_data = pd.merge(
        plot_data,
        pltassgn_df,
        left_on='PLT_CN',
        right_on='CN',
        how='inner'
    )
    
    # Get stratum variable
    if 'STRATUMCD' in plot_data.columns:
        strata_var = 'STRATUMCD'
    else:
        strata_var = 'STATECD'
    
    # Calculate by domain if specified
    if rowvar:
        # Need to get domain from trees
        check_column_exists(trees_n, [rowvar], "tree_df")
        
        # Aggregate by domain and plot
        trees_n_domain = trees_n.groupby(['PLT_CN', rowvar])['NUMER_ACRE'].sum().reset_index()
        trees_d_domain = trees_d.groupby(['PLT_CN', rowvar])['DENOM_ACRE'].sum().reset_index()
        
        domain_data = pd.merge(
            trees_n_domain,
            trees_d_domain,
            on=['PLT_CN', rowvar],
            how='outer'
        ).fillna(0)
        
        # Merge with plot data for stratum
        domain_data = pd.merge(
            domain_data,
            plot_data[['PLT_CN', strata_var]],
            on='PLT_CN'
        )
        
        # Calculate stratum means by domain
        stratum_means = domain_data.groupby([rowvar, strata_var]).agg({
            'NUMER_ACRE': ['mean', 'var'],
            'DENOM_ACRE': ['mean', 'var'],
        }).reset_index()
        
        # Flatten column names
        stratum_means.columns = [rowvar, strata_var, 'numer_mean', 'numer_var', 
                                 'denom_mean', 'denom_var']
        
        # Calculate covariance (simplified - would need actual covariance calculation)
        stratum_means['covar'] = 0  # Placeholder
        
        # Calculate ratio by domain
        domain_est = stratum_means.groupby(rowvar).agg({
            'numer_mean': 'mean',
            'numer_var': 'sum',
            'denom_mean': 'mean',
            'denom_var': 'sum',
            'covar': 'sum',
        }).reset_index()
        
        # Calculate ratio
        domain_est['RATIO'] = domain_est['numer_mean'] / domain_est['denom_mean']
        
        # Calculate ratio variance using delta method
        # Var(R) = (1/denom^2) * [numer_var + R^2*denom_var - 2*R*covar]
        domain_est['RATIO_VAR'] = (
            (1 / domain_est['denom_mean']**2) *
            (domain_est['numer_var'] + 
             domain_est['RATIO']**2 * domain_est['denom_var'] -
             2 * domain_est['RATIO'] * domain_est['covar'])
        )
        
        est_df = domain_est[[rowvar, 'RATIO', 'RATIO_VAR']].copy()
        est_df.columns = [rowvar, 'ESTIMATE', 'VARIANCE']
        
    else:
        # Overall ratio
        total_numer = plot_data['NUMER'].sum()
        total_denom = plot_data['DENOM'].sum()
        
        ratio = total_numer / total_denom if total_denom > 0 else 0
        
        # Variance calculation (simplified)
        n = len(plot_data)
        numer_var = plot_data['NUMER'].var()
        denom_var = plot_data['DENOM'].var()
        covar = plot_data[['NUMER', 'DENOM']].cov().iloc[0, 1]
        
        ratio_var = (1 / total_denom**2) * (
            numer_var + ratio**2 * denom_var - 2 * ratio * covar
        ) / n
        
        est_df = pd.DataFrame({
            'ESTIMATE': [ratio],
            'VARIANCE': [ratio_var]
        })
    
    # Calculate percent sampling error
    est_df['PSE'] = calculate_sampling_error(
        est_df['VARIANCE'].values,
        est_df['ESTIMATE'].values,
        confidence_level
    )
    
    # Prepare output
    if rowvar:
        pse_df = est_df[[rowvar, 'PSE']].copy()
    else:
        pse_df = est_df[['PSE']].copy()
    
    result = {
        'est': est_df,
        'pse': pse_df,
        'raw': {
            'n_plots': len(plot_data),
            'ratio_type': ratio_type,
        }
    }
    
    return result


def calculate_per_acre_ratio(
    numerator_var: str,
    denominator_var: str = "AREA",
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function for per-acre ratio estimates.
    
    Args:
        numerator_var: Variable to estimate per acre
        denominator_var: Denominator (usually area)
        **kwargs: Arguments passed to gb_ratio_estimates
        
    Returns:
        Dictionary with ratio estimates
    """
    return gb_ratio_estimates(
        estvarn=numerator_var,
        estvard=denominator_var,
        ratio_type="PERACRE",
        **kwargs
    )


def calculate_per_tree_ratio(
    numerator_var: str,
    denominator_var: str = "TPA_UNADJ",
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function for per-tree ratio estimates.
    
    Args:
        numerator_var: Variable to estimate per tree
        denominator_var: Denominator (usually TPA)
        **kwargs: Arguments passed to gb_ratio_estimates
        
    Returns:
        Dictionary with ratio estimates
    """
    return gb_ratio_estimates(
        estvarn=numerator_var,
        estvard=denominator_var,
        ratio_type="PERTREE",
        **kwargs
    )
