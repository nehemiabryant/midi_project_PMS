def convert_to_dicts(data, keys):
    """
    Mengubah list of tuples menjadi list of dictionaries.
    
    Parameters:
    - data: List of tuples, seperti [(id, nik, nama, ...), (), ...]
    - keys: List of keys untuk dictionary, seperti ['id', 'nik', 'nama', ...]
    
    Returns:
    - List of dictionaries.
    """
    if not data or not keys:
        return []
    
    if not all(hasattr(values, '__len__') and len(values) == len(keys) for values in data if hasattr(values, '__len__')):
        raise ValueError("Jumlah elemen dalam data tidak sesuai dengan jumlah keys")
    
    return [dict(zip(keys, values)) for values in data]