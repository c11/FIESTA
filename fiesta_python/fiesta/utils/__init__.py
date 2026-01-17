"""Utility functions for FIESTA package."""

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Union
import warnings


def check_required_params(params: Dict[str, Any], required: List[str]) -> None:
    """
    Check if required parameters are present.
    
    Args:
        params: Dictionary of parameters
        required: List of required parameter names
        
    Raises:
        ValueError: If any required parameter is missing
    """
    missing = [p for p in required if p not in params or params[p] is None]
    if missing:
        raise ValueError(f"Missing required parameters: {', '.join(missing)}")


def check_dataframe(df: Any, name: str = "data") -> pd.DataFrame:
    """
    Validate that input is a pandas DataFrame.
    
    Args:
        df: Input to validate
        name: Name for error messages
        
    Returns:
        Validated DataFrame
        
    Raises:
        TypeError: If input is not a DataFrame
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"{name} must be a pandas DataFrame")
    if df.empty:
        warnings.warn(f"{name} is empty")
    return df


def check_column_exists(df: pd.DataFrame, columns: Union[str, List[str]], 
                       df_name: str = "DataFrame") -> None:
    """
    Check if column(s) exist in DataFrame.
    
    Args:
        df: DataFrame to check
        columns: Column name or list of column names
        df_name: Name for error messages
        
    Raises:
        ValueError: If any column is missing
    """
    if isinstance(columns, str):
        columns = [columns]
    
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(
            f"Column(s) not found in {df_name}: {', '.join(missing)}"
        )


def parse_filter(filter_str: str) -> str:
    """
    Parse R-style filter expression to pandas query syntax.
    
    Args:
        filter_str: R-style filter expression
        
    Returns:
        Pandas-compatible query string
    """
    if not filter_str:
        return ""
    
    # Replace R operators with Python equivalents
    filter_str = filter_str.replace("==", "==")
    filter_str = filter_str.replace("!=", "!=")
    filter_str = filter_str.replace("%in%", "in")
    filter_str = filter_str.replace("&", " and ")
    filter_str = filter_str.replace("|", " or ")
    
    return filter_str


def format_estimate_table(est: pd.DataFrame, pse: pd.DataFrame, 
                         combine: bool = True) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """
    Format estimation and sampling error tables.
    
    Args:
        est: Estimate table
        pse: Percent sampling error table
        combine: If True, combine into one table
        
    Returns:
        Combined DataFrame or dict with separate tables
    """
    if combine:
        # Merge estimates and percent sampling errors
        result = est.copy()
        for col in pse.columns:
            if col not in est.columns or col in est.index.names:
                continue
            result[f"{col}_pse"] = pse[col]
        return result
    else:
        return {"est": est, "pse": pse}


def calculate_sampling_error(variance: np.ndarray, estimate: np.ndarray, 
                             confidence: float = 0.68) -> np.ndarray:
    """
    Calculate percent sampling error.
    
    Args:
        variance: Variance estimates
        estimate: Point estimates
        confidence: Confidence level (default 0.68 for 1 standard error)
        
    Returns:
        Percent sampling errors
    """
    std_error = np.sqrt(variance)
    
    # Avoid division by zero
    with np.errstate(divide='ignore', invalid='ignore'):
        pse = np.where(
            estimate != 0,
            (std_error / estimate) * 100,
            np.nan
        )
    
    return pse


def expand_area(stratum_means: np.ndarray, stratum_weights: np.ndarray, 
                total_area: float) -> float:
    """
    Expand stratum means to total area.
    
    Args:
        stratum_means: Mean values by stratum
        stratum_weights: Stratum weights (proportions)
        total_area: Total area to expand to
        
    Returns:
        Expanded area estimate
    """
    weighted_mean = np.sum(stratum_means * stratum_weights)
    return weighted_mean * total_area


def get_strata_weights(strata_areas: np.ndarray) -> np.ndarray:
    """
    Calculate stratum weights from areas.
    
    Args:
        strata_areas: Areas by stratum
        
    Returns:
        Stratum weights (proportions)
    """
    total_area = np.sum(strata_areas)
    if total_area == 0:
        raise ValueError("Total stratum area is zero")
    return strata_areas / total_area


def merge_dataframes(df1: pd.DataFrame, df2: pd.DataFrame, 
                     on: Union[str, List[str]], 
                     how: str = "inner",
                     validate: Optional[str] = None) -> pd.DataFrame:
    """
    Merge two DataFrames with validation.
    
    Args:
        df1: First DataFrame
        df2: Second DataFrame  
        on: Column(s) to join on
        how: Type of merge ('inner', 'left', 'right', 'outer')
        validate: Validation type for merge
        
    Returns:
        Merged DataFrame
    """
    if isinstance(on, str):
        on = [on]
    
    # Check merge keys exist
    check_column_exists(df1, on, "df1")
    check_column_exists(df2, on, "df2")
    
    return pd.merge(df1, df2, on=on, how=how, validate=validate)


class FIESTAException(Exception):
    """Base exception for FIESTA package."""
    pass


class DataValidationError(FIESTAException):
    """Exception raised for data validation errors."""
    pass


class EstimationError(FIESTAException):
    """Exception raised for estimation errors."""
    pass
