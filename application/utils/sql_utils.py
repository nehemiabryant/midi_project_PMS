from typing import Dict, Any
import datetime
import pandas as pd

def pg_interpolate_query(sql: str, params: Dict[str, Any]) -> str:
    """
    Generate executable SQL by interpolating parameters into the query.
    WARNING: For DEBUGGING only, not safe for production execution!
    
    Args:
        sql: SQL query with named parameters (:param_name)
        params: Dictionary of parameters
        
    Returns:
        Formatted SQL string that can be executed directly in SQL clients
    
    Example:
        >>> sql = "SELECT * FROM users WHERE id = :id AND name = :name"
        >>> params = {'id': 1, 'name': 'John'}
        >>> print(interpolate_query(sql, params))
        "SELECT * FROM users WHERE id = 1 AND name = 'John'"
    """
    def process_value(value: Any) -> str:
        if value is None:
            return 'NULL'
        elif isinstance(value, (int, float, bool)):
            return str(value)
        elif isinstance(value, (str, bytes)):
            return f"""'{str(value).replace("'", "''")}'"""
        elif isinstance(value, (datetime.datetime, pd.Timestamp)):
            return f"TO_DATE('{value.strftime('%Y-%m-%d %H:%M:%S')}', 'YYYY-MM-DD HH24:MI:SS')"
        elif isinstance(value, datetime.date):
            return f"TO_DATE('{value.strftime('%Y-%m-%d')}', 'YYYY-MM-DD')"
        else:
            return f"'{str(value)}'"
    
    interpolated = sql
    for key, value in params.items():
        placeholder = f':{key}'
        if placeholder in interpolated:
            interpolated = interpolated.replace(placeholder, process_value(value))
    
    return interpolated