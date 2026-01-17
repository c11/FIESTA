"""Data filtering functions - Python implementation of datFilter.R"""

import pandas as pd
from typing import Optional, Union, List, Dict, Any
import warnings

from fiesta.utils import (
    check_dataframe,
    check_column_exists,
    parse_filter,
    DataValidationError,
)


def filter_data(
    x: Union[pd.DataFrame, str],
    xfilter: Optional[str] = None,
    xfiltervar: Optional[str] = None,
    other_tables: Optional[Dict[str, pd.DataFrame]] = None,
    unique_id: str = "PLT_CN",
    return_filter: bool = True,
    stop_if_null: bool = False,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Filter data table by specified filter expression.
    
    This function subsets a DataFrame by specified filter(s), similar to R's
    datFilter function. It can also filter related tables using a unique identifier.
    
    Args:
        x: DataFrame or path to CSV file to filter
        xfilter: Filter expression in R or pandas query syntax
            Examples: "STATUSCD == 1", "INVYR >= 2010 & INVYR <= 2015"
        xfiltervar: Specific variable to filter on (if known)
        other_tables: Dict of other DataFrames to filter by the same unique_id
        unique_id: Column name for unique identifier to link tables
        return_filter: If True, return the filter expression used
        stop_if_null: If True, raise error if result is empty
        verbose: If True, print information messages
        
    Returns:
        Dictionary containing:
            - 'xf': Filtered DataFrame
            - 'xfilter': Filter expression used (if return_filter=True)
            - Other filtered tables (if other_tables provided)
            
    Raises:
        DataValidationError: If filter removes all records or data is invalid
        
    Examples:
        >>> # Filter for specific forest type
        >>> result = filter_data(df, xfilter="FORTYPCD == 182")
        >>> filtered_df = result['xf']
        
        >>> # Filter with multiple conditions
        >>> result = filter_data(
        ...     df, 
        ...     xfilter="FORTYPCD == 221 & STDSZCD == 3"
        ... )
        
        >>> # Filter multiple related tables
        >>> result = filter_data(
        ...     plots_df,
        ...     xfilter="STATUSCD == 1",
        ...     other_tables={'cond': cond_df, 'tree': tree_df},
        ...     unique_id='PLT_CN'
        ... )
    """
    # Load data if path provided
    if isinstance(x, str):
        try:
            x = pd.read_csv(x)
        except Exception as e:
            raise DataValidationError(f"Failed to read CSV file: {e}")
    
    # Validate input DataFrame
    x = check_dataframe(x, "x")
    
    # Make a copy to avoid modifying original
    xf = x.copy()
    
    # If no filter provided, return original data
    if xfilter is None and xfiltervar is None:
        if verbose:
            print("No filter provided, returning original data")
        result = {"xf": xf}
        if return_filter:
            result["xfilter"] = None
        return result
    
    # Parse and apply filter
    if xfilter is not None:
        # Convert R-style filter to pandas query syntax
        filter_expr = parse_filter(xfilter)
        
        try:
            xf = xf.query(filter_expr)
        except Exception as e:
            raise DataValidationError(
                f"Invalid filter expression '{xfilter}': {e}"
            )
        
        if verbose:
            print(f"Applied filter: {xfilter}")
            print(f"Records before filter: {len(x)}")
            print(f"Records after filter: {len(xf)}")
    
    elif xfiltervar is not None:
        # Filter by specific variable (simplified version)
        check_column_exists(xf, xfiltervar, "x")
        # This would open a GUI in R, but we'll just return data with that column
        if verbose:
            print(f"Filter variable '{xfiltervar}' specified")
    
    # Check if filter removed all records
    if len(xf) == 0:
        msg = "Filter removed all records"
        if stop_if_null:
            raise DataValidationError(msg)
        else:
            warnings.warn(msg)
    
    # Build result dictionary
    result = {"xf": xf}
    
    if return_filter:
        result["xfilter"] = xfilter
    
    # Filter other tables if provided
    if other_tables is not None and len(xf) > 0:
        # Check unique_id exists in main table
        check_column_exists(xf, unique_id, "x")
        
        # Get unique IDs from filtered main table
        filter_ids = xf[unique_id].unique()
        
        for table_name, table_df in other_tables.items():
            table_df = check_dataframe(table_df, table_name)
            
            # Check if unique_id exists in other table
            if unique_id in table_df.columns:
                # Filter other table by unique IDs
                filtered_table = table_df[table_df[unique_id].isin(filter_ids)]
                result[f"{table_name}_filtered"] = filtered_table
                
                if verbose:
                    print(f"Filtered {table_name}: {len(table_df)} -> {len(filtered_table)} records")
            else:
                warnings.warn(
                    f"Column '{unique_id}' not found in table '{table_name}', skipping"
                )
    
    return result


def filter_by_values(
    df: pd.DataFrame,
    column: str,
    values: Union[List, Any],
    exclude: bool = False,
) -> pd.DataFrame:
    """
    Filter DataFrame by specific values in a column.
    
    Args:
        df: DataFrame to filter
        column: Column name to filter on
        values: Value or list of values to filter by
        exclude: If True, exclude the values instead of including them
        
    Returns:
        Filtered DataFrame
        
    Examples:
        >>> # Include specific values
        >>> filtered = filter_by_values(df, 'FORTYPCD', [182, 184, 221])
        
        >>> # Exclude specific values
        >>> filtered = filter_by_values(df, 'STATUSCD', [0], exclude=True)
    """
    df = check_dataframe(df, "df")
    check_column_exists(df, column, "df")
    
    if not isinstance(values, list):
        values = [values]
    
    if exclude:
        return df[~df[column].isin(values)]
    else:
        return df[df[column].isin(values)]


def filter_by_range(
    df: pd.DataFrame,
    column: str,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    inclusive: str = "both",
) -> pd.DataFrame:
    """
    Filter DataFrame by value range.
    
    Args:
        df: DataFrame to filter
        column: Column name to filter on
        min_val: Minimum value (inclusive)
        max_val: Maximum value (inclusive)
        inclusive: 'both', 'left', 'right', or 'neither'
        
    Returns:
        Filtered DataFrame
        
    Examples:
        >>> # Filter by year range
        >>> filtered = filter_by_range(df, 'INVYR', min_val=2010, max_val=2020)
    """
    df = check_dataframe(df, "df")
    check_column_exists(df, column, "df")
    
    mask = pd.Series([True] * len(df), index=df.index)
    
    if min_val is not None:
        if inclusive in ["both", "left"]:
            mask &= df[column] >= min_val
        else:
            mask &= df[column] > min_val
    
    if max_val is not None:
        if inclusive in ["both", "right"]:
            mask &= df[column] <= max_val
        else:
            mask &= df[column] < max_val
    
    return df[mask]
