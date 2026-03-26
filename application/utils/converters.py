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

def parse_rows(db_result: dict) -> list:
    """
    Parse hasil selectDataHeader ke list of dicts.

    Parameters:
    - db_result: Response dari DatabasePG (format: {'status': bool, 'data': [headers, rows]})

    Returns:
    - List of dictionaries, atau [] jika gagal/kosong.
    """
    if not db_result.get('status'):
        return []
    raw = db_result.get('data', [[], []])
    if not raw or len(raw) < 2 or not raw[1]:
        return []
    return convert_to_dicts(raw[1], raw[0])

def parse_single_row(db_result: dict) -> dict | None:
    """
    Parse hasil selectDataHeader ke single dict (baris pertama).

    Parameters:
    - db_result: Response dari DatabasePG (format: {'status': bool, 'data': [headers, rows]})

    Returns:
    - Dictionary dari baris pertama, atau None jika gagal/kosong.
    """
    result = parse_rows(db_result)
    return result[0] if result else None