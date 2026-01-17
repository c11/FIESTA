"""Functions for reading FIA data from CSV files."""

import pandas as pd
from pathlib import Path
from typing import Optional, Union, List, Dict
import warnings

from fiesta.utils import DataValidationError


def get_csv(
    file_path: Union[str, Path],
    filter_expr: Optional[str] = None,
    columns: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Read CSV file with optional filtering.
    
    Args:
        file_path: Path to CSV file
        filter_expr: Optional filter expression (pandas query syntax)
        columns: Optional list of columns to read
        
    Returns:
        DataFrame with CSV data
        
    Examples:
        >>> # Read full CSV
        >>> df = get_csv("WY_PLOT.csv")
        
        >>> # Read with column selection
        >>> df = get_csv(
        ...     "WY_PLOT.csv",
        ...     columns=['CN', 'INVYR', 'STATECD', 'PLOT']
        ... )
        
        >>> # Read with filter
        >>> df = get_csv(
        ...     "WY_PLOT.csv",
        ...     filter_expr="INVYR >= 2010"
        ... )
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise DataValidationError(f"File not found: {file_path}")
    
    try:
        # Read CSV
        if columns is not None:
            df = pd.read_csv(file_path, usecols=columns, low_memory=False)
        else:
            df = pd.read_csv(file_path, low_memory=False)
        
        # Apply filter if provided
        if filter_expr is not None:
            df = df.query(filter_expr)
        
        return df
    
    except Exception as e:
        raise DataValidationError(f"Error reading CSV file: {e}")


def read_multiple_csvs(
    file_paths: List[Union[str, Path]],
    combine: bool = True,
    **kwargs
) -> Union[pd.DataFrame, List[pd.DataFrame]]:
    """
    Read multiple CSV files.
    
    Args:
        file_paths: List of paths to CSV files
        combine: If True, concatenate all DataFrames
        **kwargs: Additional arguments passed to get_csv()
        
    Returns:
        Combined DataFrame or list of DataFrames
        
    Examples:
        >>> # Read and combine multiple state files
        >>> files = ['WY_PLOT.csv', 'MT_PLOT.csv', 'ID_PLOT.csv']
        >>> combined_df = read_multiple_csvs(files)
    """
    dfs = []
    
    for file_path in file_paths:
        try:
            df = get_csv(file_path, **kwargs)
            dfs.append(df)
        except Exception as e:
            warnings.warn(f"Error reading {file_path}: {e}")
            continue
    
    if not dfs:
        raise DataValidationError("No valid CSV files could be read")
    
    if combine:
        return pd.concat(dfs, ignore_index=True)
    else:
        return dfs


def read_csv_by_state(
    data_dir: Union[str, Path],
    table_name: str,
    states: List[str],
    **kwargs
) -> pd.DataFrame:
    """
    Read FIA CSV files for multiple states.
    
    Args:
        data_dir: Directory containing FIA CSV files
        table_name: FIA table name (e.g., 'PLOT', 'COND', 'TREE')
        states: List of state abbreviations
        **kwargs: Additional arguments passed to get_csv()
        
    Returns:
        Combined DataFrame with data from all states
        
    Examples:
        >>> # Read plot data for multiple states
        >>> plots = read_csv_by_state(
        ...     '/path/to/fia/data',
        ...     'PLOT',
        ...     ['WY', 'MT', 'ID']
        ... )
    """
    data_dir = Path(data_dir)
    
    if not data_dir.exists():
        raise DataValidationError(f"Data directory not found: {data_dir}")
    
    file_paths = []
    for state in states:
        state_upper = state.upper()
        file_path = data_dir / f"{state_upper}_{table_name}.csv"
        
        if file_path.exists():
            file_paths.append(file_path)
        else:
            warnings.warn(f"File not found for state {state_upper}: {file_path}")
    
    return read_multiple_csvs(file_paths, combine=True, **kwargs)
