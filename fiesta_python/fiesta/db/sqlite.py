"""Functions for working with SQLite FIA databases."""

import pandas as pd
import sqlite3
from pathlib import Path
from typing import Optional, Union, List
import warnings

from fiesta.utils import DataValidationError


def get_sqlite_connection(db_path: Union[str, Path]) -> sqlite3.Connection:
    """
    Create connection to SQLite database.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        SQLite connection object
        
    Examples:
        >>> conn = get_sqlite_connection("FIADB.db")
    """
    db_path = Path(db_path)
    
    if not db_path.exists():
        raise DataValidationError(f"Database file not found: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except Exception as e:
        raise DataValidationError(f"Error connecting to database: {e}")


def query_sqlite(
    db_path: Union[str, Path],
    query: str,
    params: Optional[tuple] = None,
) -> pd.DataFrame:
    """
    Execute SQL query on SQLite database.
    
    Args:
        db_path: Path to SQLite database file
        query: SQL query string
        params: Optional tuple of query parameters
        
    Returns:
        DataFrame with query results
        
    Examples:
        >>> # Simple query
        >>> df = query_sqlite(
        ...     "FIADB.db",
        ...     "SELECT * FROM PLOT WHERE STATECD = 56"
        ... )
        
        >>> # Parameterized query
        >>> df = query_sqlite(
        ...     "FIADB.db",
        ...     "SELECT * FROM PLOT WHERE STATECD = ? AND INVYR >= ?",
        ...     params=(56, 2010)
        ... )
    """
    conn = get_sqlite_connection(db_path)
    
    try:
        if params is not None:
            df = pd.read_sql_query(query, conn, params=params)
        else:
            df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        raise DataValidationError(f"Error executing query: {e}")
    finally:
        conn.close()


def get_table_list(db_path: Union[str, Path]) -> List[str]:
    """
    Get list of tables in SQLite database.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        List of table names
        
    Examples:
        >>> tables = get_table_list("FIADB.db")
        >>> print(tables)
    """
    query = "SELECT name FROM sqlite_master WHERE type='table'"
    df = query_sqlite(db_path, query)
    return df['name'].tolist()


def get_table_columns(
    db_path: Union[str, Path],
    table_name: str,
) -> pd.DataFrame:
    """
    Get column information for a table.
    
    Args:
        db_path: Path to SQLite database file
        table_name: Name of the table
        
    Returns:
        DataFrame with column information
        
    Examples:
        >>> cols = get_table_columns("FIADB.db", "PLOT")
    """
    query = f"PRAGMA table_info({table_name})"
    return query_sqlite(db_path, query)


def get_plots_from_sqlite(
    db_path: Union[str, Path],
    states: Optional[List[Union[str, int]]] = None,
    invyrs: Optional[List[int]] = None,
    tables: List[str] = ["PLOT", "COND", "TREE"],
) -> dict:
    """
    Retrieve FIA plots from SQLite database.
    
    Args:
        db_path: Path to SQLite FIA database
        states: State codes or abbreviations
        invyrs: Inventory years
        tables: List of table names to retrieve
        
    Returns:
        Dictionary of DataFrames
        
    Examples:
        >>> fia_data = get_plots_from_sqlite(
        ...     "FIADB.db",
        ...     states=[56],  # Wyoming
        ...     invyrs=[2015, 2016, 2017]
        ... )
    """
    result = {}
    
    # State code mapping
    state_codes = {
        'WY': 56, 'MT': 30, 'ID': 16, 'CO': 8, 'UT': 49,
    }
    
    # Convert state abbreviations to codes
    if states:
        state_cd_list = []
        for state in states:
            if isinstance(state, str) and state.upper() in state_codes:
                state_cd_list.append(state_codes[state.upper()])
            else:
                state_cd_list.append(state)
    else:
        state_cd_list = None
    
    for table in tables:
        # Build query
        query = f"SELECT * FROM {table}"
        conditions = []
        params = []
        
        if state_cd_list and table in ["PLOT", "COND", "TREE"]:
            placeholders = ','.join('?' * len(state_cd_list))
            conditions.append(f"STATECD IN ({placeholders})")
            params.extend(state_cd_list)
        
        if invyrs and table in ["PLOT", "COND"]:
            placeholders = ','.join('?' * len(invyrs))
            conditions.append(f"INVYR IN ({placeholders})")
            params.extend(invyrs)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        try:
            df = query_sqlite(db_path, query, tuple(params) if params else None)
            result[table] = df
        except Exception as e:
            warnings.warn(f"Error querying {table}: {e}")
    
    return result
