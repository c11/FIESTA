"""Photo-Based (PB) estimation module.

Based on Patterson (2012) photo-based estimators for photo-based inventory.
Generates percent, area or ratio-of-means estimates with associated sampling error.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
import warnings

from fiesta.utils import (
    check_dataframe,
    check_column_exists,
    calculate_sampling_error,
    EstimationError,
)


def pb_estimates(
    pnt_df: pd.DataFrame,
    plt_df: pd.DataFrame,
    unitarea_df: pd.DataFrame,
    tabtype: str = "PCT",
    rowvar: Optional[str] = None,
    colvar: Optional[str] = None,
    nonsamp_pntfilter: Optional[str] = None,
    pntfilter: Optional[str] = None,
    landarea: str = "ALL",
    unitvar: str = "ESTN_UNIT",
    confidence_level: float = 0.68,
) -> Dict[str, Any]:
    """
    Generate photo-based estimates with sampling error.
    
    Uses Patterson (2012) photo-based estimators for calculating percent cover
    or area estimates by domain and estimation unit.
    
    Args:
        pnt_df: Point data with photo interpretation
        plt_df: Plot assignment data
        unitarea_df: Area by estimation unit
        tabtype: Type of table ('PCT' for percent, 'AREA' for area)
        rowvar: Row domain variable
        colvar: Column domain variable
        nonsamp_pntfilter: Filter for nonsampled points
        pntfilter: Global filter for point data
        landarea: Land area filter ('ALL', 'CHANGE')
        unitvar: Estimation unit variable
        confidence_level: Confidence level for sampling error
        
    Returns:
        Dictionary with estimates, percent sampling errors, and raw data
        
    Examples:
        >>> # Percent cover by land cover class
        >>> result = pb_estimates(
        ...     pnt_df=points,
        ...     plt_df=plots,
        ...     unitarea_df=unit_areas,
        ...     tabtype='PCT',
        ...     rowvar='cover_1',
        ...     nonsamp_pntfilter='cover_1 != 999'
        ... )
        
        >>> # Area estimates by county
        >>> result = pb_estimates(
        ...     pnt_df=points,
        ...     plt_df=plots,
        ...     unitarea_df=unit_areas,
        ...     tabtype='AREA',
        ...     rowvar='cover_1',
        ...     unitvar='COUNTY'
        ... )
    """
    # Validate inputs
    pnt_df = check_dataframe(pnt_df, "pnt_df")
    plt_df = check_dataframe(plt_df, "plt_df")
    unitarea_df = check_dataframe(unitarea_df, "unitarea_df")
    
    # Make copies
    pnt = pnt_df.copy()
    plt = plt_df.copy()
    
    # Apply filters
    if pntfilter:
        pnt = pnt.query(pntfilter)
    if nonsamp_pntfilter:
        pnt = pnt.query(nonsamp_pntfilter)
    
    # Merge point and plot data
    if 'PLT_CN' in pnt.columns and 'CN' in plt.columns:
        pnt = pd.merge(pnt, plt, left_on='PLT_CN', right_on='CN', how='inner')
    elif 'PLOT_ID' in pnt.columns and 'PLOT_ID' in plt.columns:
        pnt = pd.merge(pnt, plt, on='PLOT_ID', how='inner')
    else:
        raise EstimationError("Cannot merge point and plot data - missing join columns")
    
    # Get unit areas
    check_column_exists(unitarea_df, [unitvar, 'AREA'], "unitarea_df")
    unit_areas = unitarea_df.set_index(unitvar)['AREA'].to_dict()
    
    # Calculate by domain if specified
    if rowvar:
        check_column_exists(pnt, [rowvar, unitvar], "pnt_df")
        
        # Count points by domain and unit
        pnt_counts = pnt.groupby([unitvar, rowvar]).size().reset_index(name='n_points')
        total_counts = pnt.groupby(unitvar).size().reset_index(name='n_total')
        
        # Merge counts
        domain_data = pd.merge(pnt_counts, total_counts, on=unitvar)
        
        # Calculate proportions
        domain_data['phat'] = domain_data['n_points'] / domain_data['n_total']
        
        # Calculate variance (simple random sampling)
        domain_data['phat_var'] = (
            domain_data['phat'] * (1 - domain_data['phat']) / 
            domain_data['n_total']
        )
        
        # Get unit areas
        domain_data['UNIT_AREA'] = domain_data[unitvar].map(unit_areas)
        
        if tabtype == 'PCT':
            # Percent estimates
            domain_data['ESTIMATE'] = domain_data['phat'] * 100
            domain_data['VARIANCE'] = domain_data['phat_var'] * 10000
        else:  # AREA
            # Area estimates
            domain_data['ESTIMATE'] = domain_data['phat'] * domain_data['UNIT_AREA']
            domain_data['VARIANCE'] = domain_data['phat_var'] * domain_data['UNIT_AREA']**2
        
        # Calculate PSE
        domain_data['PSE'] = calculate_sampling_error(
            domain_data['VARIANCE'].values,
            domain_data['ESTIMATE'].values,
            confidence_level
        )
        
        # Prepare output
        est_df = domain_data[[unitvar, rowvar, 'ESTIMATE', 'VARIANCE']].copy()
        pse_df = domain_data[[unitvar, rowvar, 'PSE']].copy()
        
        raw_data = {
            'pnt_counts': pnt_counts,
            'proportions': domain_data[
                [unitvar, rowvar, 'phat', 'phat_var', 'n_points', 'n_total']
            ].copy()
        }
        
    else:
        # Overall estimates by unit
        total_counts = pnt.groupby(unitvar).size().reset_index(name='n_total')
        total_counts['UNIT_AREA'] = total_counts[unitvar].map(unit_areas)
        
        if tabtype == 'PCT':
            # Overall percent (100% by definition if no domain)
            total_counts['ESTIMATE'] = 100.0
            total_counts['VARIANCE'] = 0.0
        else:  # AREA
            # Total area
            total_counts['ESTIMATE'] = total_counts['UNIT_AREA']
            total_counts['VARIANCE'] = 0.0
        
        total_counts['PSE'] = 0.0
        
        est_df = total_counts[[unitvar, 'ESTIMATE', 'VARIANCE']].copy()
        pse_df = total_counts[[unitvar, 'PSE']].copy()
        
        raw_data = {
            'total_counts': total_counts
        }
    
    result = {
        'est': est_df,
        'pse': pse_df,
        'raw': raw_data
    }
    
    return result


def pb_ratio_estimates(
    pnt_df: pd.DataFrame,
    plt_df: pd.DataFrame,
    unitarea_df: pd.DataFrame,
    numerator: str,
    denominator: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate ratio estimates for photo-based data.
    
    Args:
        pnt_df: Point data
        plt_df: Plot assignment data
        unitarea_df: Area by estimation unit
        numerator: Numerator variable
        denominator: Denominator variable
        **kwargs: Additional arguments for pb_estimates
        
    Returns:
        Dictionary with ratio estimates
    """
    # Get numerator estimates
    num_result = pb_estimates(
        pnt_df=pnt_df,
        plt_df=plt_df,
        unitarea_df=unitarea_df,
        rowvar=numerator,
        **kwargs
    )
    
    # Get denominator estimates
    denom_result = pb_estimates(
        pnt_df=pnt_df,
        plt_df=plt_df,
        unitarea_df=unitarea_df,
        rowvar=denominator,
        **kwargs
    )
    
    # Calculate ratio
    num_est = num_result['est']
    denom_est = denom_result['est']
    
    # Merge numerator and denominator
    ratio_data = pd.merge(
        num_est,
        denom_est,
        on=['ESTN_UNIT'] if 'ESTN_UNIT' in num_est.columns else [],
        suffixes=('_num', '_denom')
    )
    
    # Calculate ratio
    ratio_data['RATIO'] = (
        ratio_data['ESTIMATE_num'] / ratio_data['ESTIMATE_denom']
    )
    
    # Calculate ratio variance (delta method)
    # Var(R) = (1/denom^2) * [num_var + R^2*denom_var - 2*R*covar]
    # Simplified: assuming covar = 0
    ratio_data['RATIO_VAR'] = (
        (1 / ratio_data['ESTIMATE_denom']**2) *
        (ratio_data['VARIANCE_num'] + 
         ratio_data['RATIO']**2 * ratio_data['VARIANCE_denom'])
    )
    
    # Calculate PSE
    ratio_data['PSE'] = calculate_sampling_error(
        ratio_data['RATIO_VAR'].values,
        ratio_data['RATIO'].values,
        kwargs.get('confidence_level', 0.68)
    )
    
    return {
        'est': ratio_data[['RATIO', 'RATIO_VAR']],
        'pse': ratio_data[['PSE']],
        'raw': {
            'numerator': num_result['raw'],
            'denominator': denom_result['raw']
        }
    }


__all__ = [
    "pb_estimates",
    "pb_ratio_estimates",
]
