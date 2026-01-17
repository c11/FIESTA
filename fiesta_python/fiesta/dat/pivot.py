"""Data pivoting functions - Python implementation of datPivot.R"""

import pandas as pd
from typing import Optional, Union, List, Any
import warnings

from fiesta.utils import check_dataframe, check_column_exists


def pivot_data(
    df: pd.DataFrame,
    index: Union[str, List[str]],
    columns: Union[str, List[str]],
    values: Union[str, List[str]],
    aggfunc: Union[str, callable] = "sum",
    fill_value: Any = None,
    margins: bool = False,
    margins_name: str = "All",
) -> pd.DataFrame:
    """
    Pivot (reshape) data from long to wide format.
    
    Args:
        df: Input DataFrame
        index: Column(s) to use as index (rows)
        columns: Column(s) to use as columns
        values: Column(s) to aggregate
        aggfunc: Aggregation function ('sum', 'mean', 'count', etc.)
        fill_value: Value to replace missing values
        margins: If True, add row/column totals
        margins_name: Name for the margin row/column
        
    Returns:
        Pivoted DataFrame
        
    Examples:
        >>> # Pivot area by forest type and size class
        >>> pivoted = pivot_data(
        ...     df,
        ...     index='FORTYPCD',
        ...     columns='STDSZCD',
        ...     values='AREA',
        ...     aggfunc='sum'
        ... )
        
        >>> # Multiple aggregation functions
        >>> pivoted = pivot_data(
        ...     df,
        ...     index='FORTYPCD',
        ...     columns='INVYR',
        ...     values='AREA',
        ...     aggfunc=['sum', 'mean', 'count']
        ... )
    """
    df = check_dataframe(df, "df")
    
    # Ensure lists
    if isinstance(index, str):
        index_list = [index]
    else:
        index_list = list(index)
    
    if isinstance(columns, str):
        columns_list = [columns]
    else:
        columns_list = list(columns)
    
    if isinstance(values, str):
        values_list = [values]
    else:
        values_list = list(values)
    
    # Check columns exist
    all_cols = index_list + columns_list + values_list
    check_column_exists(df, all_cols, "df")
    
    # Create pivot table
    result = pd.pivot_table(
        df,
        index=index,
        columns=columns,
        values=values,
        aggfunc=aggfunc,
        fill_value=fill_value,
        margins=margins,
        margins_name=margins_name,
    )
    
    return result


def unpivot_data(
    df: pd.DataFrame,
    id_vars: Optional[Union[str, List[str]]] = None,
    value_vars: Optional[Union[str, List[str]]] = None,
    var_name: str = "variable",
    value_name: str = "value",
) -> pd.DataFrame:
    """
    Unpivot (melt) data from wide to long format.
    
    Args:
        df: Input DataFrame
        id_vars: Column(s) to keep as identifier variables
        value_vars: Column(s) to unpivot (if None, use all non-id columns)
        var_name: Name for the variable column
        value_name: Name for the value column
        
    Returns:
        Unpivoted DataFrame
        
    Examples:
        >>> # Convert wide format to long format
        >>> long_df = unpivot_data(
        ...     wide_df,
        ...     id_vars=['FORTYPCD'],
        ...     value_vars=['AREA_2010', 'AREA_2015', 'AREA_2020'],
        ...     var_name='YEAR',
        ...     value_name='AREA'
        ... )
    """
    df = check_dataframe(df, "df")
    
    result = pd.melt(
        df,
        id_vars=id_vars,
        value_vars=value_vars,
        var_name=var_name,
        value_name=value_name,
    )
    
    return result


def reshape_long_to_wide(
    df: pd.DataFrame,
    id_vars: Union[str, List[str]],
    time_var: str,
    value_vars: Union[str, List[str]],
    sep: str = "_",
) -> pd.DataFrame:
    """
    Reshape data from long to wide format, keeping multiple value columns.
    
    Args:
        df: Input DataFrame
        id_vars: Column(s) that identify observations
        time_var: Column that identifies time/category for pivoting
        value_vars: Column(s) to reshape
        sep: Separator for new column names
        
    Returns:
        Wide format DataFrame
        
    Examples:
        >>> # Reshape tree data by year
        >>> wide_df = reshape_long_to_wide(
        ...     df,
        ...     id_vars='PLOT_ID',
        ...     time_var='INVYR',
        ...     value_vars=['VOLUME', 'BIOMASS']
        ... )
    """
    df = check_dataframe(df, "df")
    
    if isinstance(id_vars, str):
        id_vars = [id_vars]
    if isinstance(value_vars, str):
        value_vars = [value_vars]
    
    check_column_exists(df, id_vars + [time_var] + value_vars, "df")
    
    # Use pivot for each value variable and concatenate
    result = df[id_vars].drop_duplicates().reset_index(drop=True)
    
    for val_var in value_vars:
        pivot = df.pivot(
            index=id_vars,
            columns=time_var,
            values=val_var,
        )
        
        # Flatten column names
        pivot.columns = [f"{val_var}{sep}{col}" for col in pivot.columns]
        pivot = pivot.reset_index()
        
        # Merge with result
        result = pd.merge(result, pivot, on=id_vars, how='outer')
    
    return result


def aggregate_data(
    df: pd.DataFrame,
    group_vars: Union[str, List[str]],
    value_vars: Union[str, List[str], None] = None,
    aggfunc: Union[str, Dict, List] = "sum",
) -> pd.DataFrame:
    """
    Aggregate data by group variables.
    
    Args:
        df: Input DataFrame
        group_vars: Column(s) to group by
        value_vars: Column(s) to aggregate (if None, aggregate all numeric)
        aggfunc: Aggregation function(s)
        
    Returns:
        Aggregated DataFrame
        
    Examples:
        >>> # Sum area by forest type
        >>> agg = aggregate_data(
        ...     df,
        ...     group_vars='FORTYPCD',
        ...     value_vars='AREA',
        ...     aggfunc='sum'
        ... )
        
        >>> # Multiple aggregations
        >>> agg = aggregate_data(
        ...     df,
        ...     group_vars=['FORTYPCD', 'STDSZCD'],
        ...     value_vars='AREA',
        ...     aggfunc={'AREA': ['sum', 'mean', 'count']}
        ... )
    """
    df = check_dataframe(df, "df")
    
    if isinstance(group_vars, str):
        group_vars = [group_vars]
    
    check_column_exists(df, group_vars, "df")
    
    if value_vars is None:
        # Aggregate all numeric columns
        result = df.groupby(group_vars).agg(aggfunc)
    else:
        if isinstance(value_vars, str):
            value_vars = [value_vars]
        check_column_exists(df, value_vars, "df")
        result = df.groupby(group_vars)[value_vars].agg(aggfunc)
    
    result = result.reset_index()
    
    return result
