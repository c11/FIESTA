"""Frequency table functions - Python implementation of datFreq.R"""

import pandas as pd
import numpy as np
from typing import Optional, Union, List
import warnings

from fiesta.utils import check_dataframe, check_column_exists


def frequency_table(
    df: pd.DataFrame,
    variables: Union[str, List[str]],
    weights: Optional[str] = None,
    normalize: bool = False,
    dropna: bool = True,
    sort_by_freq: bool = False,
) -> pd.DataFrame:
    """
    Create frequency table for categorical variables.
    
    Args:
        df: Input DataFrame
        variables: Column name(s) for frequency calculation
        weights: Optional column name for weighted frequencies
        normalize: If True, return proportions instead of counts
        dropna: If True, exclude NaN values
        sort_by_freq: If True, sort results by frequency
        
    Returns:
        DataFrame with frequency counts/proportions
        
    Examples:
        >>> # Simple frequency table
        >>> freq = frequency_table(df, 'FORTYPCD')
        
        >>> # Two-way frequency table
        >>> freq = frequency_table(df, ['FORTYPCD', 'STDSZCD'])
        
        >>> # Weighted frequencies as proportions
        >>> freq = frequency_table(
        ...     df, 
        ...     'FORTYPCD',
        ...     weights='AREA',
        ...     normalize=True
        ... )
    """
    df = check_dataframe(df, "df")
    
    if isinstance(variables, str):
        variables = [variables]
    
    check_column_exists(df, variables, "df")
    
    if weights is not None:
        check_column_exists(df, weights, "df")
    
    # Create frequency table
    if weights is None:
        if len(variables) == 1:
            result = df[variables[0]].value_counts(
                normalize=normalize,
                dropna=dropna
            ).reset_index()
            result.columns = [variables[0], 'count' if not normalize else 'proportion']
        else:
            result = df.groupby(variables, dropna=dropna).size().reset_index(name='count')
            if normalize:
                result['proportion'] = result['count'] / result['count'].sum()
    else:
        # Weighted frequency
        if len(variables) == 1:
            result = df.groupby(variables[0], dropna=dropna)[weights].sum().reset_index()
            result.columns = [variables[0], 'weighted_count']
        else:
            result = df.groupby(variables, dropna=dropna)[weights].sum().reset_index()
            result.columns = list(variables) + ['weighted_count']
        
        if normalize:
            total = result['weighted_count'].sum()
            result['proportion'] = result['weighted_count'] / total
    
    # Sort if requested
    if sort_by_freq:
        count_col = 'proportion' if normalize else ('weighted_count' if weights else 'count')
        result = result.sort_values(count_col, ascending=False)
    
    return result


def crosstab(
    df: pd.DataFrame,
    row_var: str,
    col_var: str,
    values: Optional[str] = None,
    aggfunc: str = "count",
    normalize: Union[bool, str] = False,
    margins: bool = False,
) -> pd.DataFrame:
    """
    Create cross-tabulation of two variables.
    
    Args:
        df: Input DataFrame
        row_var: Column name for row variable
        col_var: Column name for column variable
        values: Column name for values to aggregate (if not counting)
        aggfunc: Aggregation function ('count', 'sum', 'mean', etc.)
        normalize: Normalize over 'all', 'index', 'columns', or False
        margins: If True, add row/column totals
        
    Returns:
        Cross-tabulation DataFrame
        
    Examples:
        >>> # Simple cross-tab
        >>> ct = crosstab(df, 'FORTYPCD', 'STDSZCD')
        
        >>> # Weighted cross-tab with totals
        >>> ct = crosstab(
        ...     df,
        ...     'FORTYPCD',
        ...     'STDSZCD',
        ...     values='AREA',
        ...     aggfunc='sum',
        ...     margins=True
        ... )
    """
    df = check_dataframe(df, "df")
    check_column_exists(df, [row_var, col_var], "df")
    
    if values is not None:
        check_column_exists(df, values, "df")
        result = pd.crosstab(
            df[row_var],
            df[col_var],
            values=df[values],
            aggfunc=aggfunc,
            normalize=normalize,
            margins=margins,
        )
    else:
        result = pd.crosstab(
            df[row_var],
            df[col_var],
            normalize=normalize,
            margins=margins,
        )
    
    return result


def frequency_summary(
    df: pd.DataFrame,
    variables: Union[str, List[str]],
    weights: Optional[str] = None,
) -> pd.DataFrame:
    """
    Create detailed frequency summary with statistics.
    
    Args:
        df: Input DataFrame
        variables: Column name(s) for frequency calculation
        weights: Optional column name for weighted frequencies
        
    Returns:
        DataFrame with count, percent, cumulative percent, etc.
        
    Examples:
        >>> summary = frequency_summary(df, 'FORTYPCD')
    """
    freq = frequency_table(df, variables, weights=weights, normalize=False)
    
    count_col = 'weighted_count' if weights else 'count'
    total = freq[count_col].sum()
    
    freq['percent'] = (freq[count_col] / total) * 100
    freq['cumulative_count'] = freq[count_col].cumsum()
    freq['cumulative_percent'] = freq['percent'].cumsum()
    
    return freq
