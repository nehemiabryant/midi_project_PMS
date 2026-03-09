def convert_nulls(params: dict) -> dict:
    import pandas as pd
    
    """
    Convert all pandas/numpy nan values to None, and handle booleans
    
    Args:
        params: Dictionary of parameters to be cleaned
        
    Returns:
        Dictionary with cleaned values
    
    Example:
        >>> params = {'flag': False, 'name': np.nan}
        >>> convert_nulls(params)
        {'flag': 'False', 'name': None}
    """
    cleaned = {}
    for key, value in params.items():
        if pd.isna(value) or value in ['nan', 'NULL', None]:
            cleaned[key] = None
        elif isinstance(value, bool):
            cleaned[key] = str(value)  # Convert True/False to string
        else:
            cleaned[key] = value
    return cleaned