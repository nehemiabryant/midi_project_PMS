from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_WIB = ZoneInfo('Asia/Jakarta')


def to_wib(dt):
    """Konversi datetime UTC dari DB ke WIB (UTC+7). Return None jika input None."""
    if dt is None:
        return None
    if not hasattr(dt, 'tzinfo'):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_WIB)


def format_wib(dt):
    """Format datetime UTC ke string lengkap WIB: '08 Apr 2026 14:30 WIB'. Return '-' jika None."""
    wib_dt = to_wib(dt)
    if wib_dt is None:
        return '-'
    return wib_dt.strftime('%d %b %Y %H:%M:%S')


def format_date_wib(dt):
    """Format date (tanpa jam) ke string: '08 Apr 2026'. Untuk target_date, actual_date. Return '-' jika None."""
    if dt is None:
        return '-'
    if hasattr(dt, 'strftime'):
        return dt.strftime('%d %b %Y')
    return str(dt)


def parse_period(value):
    """
    Fungsi untuk memparsing input periode dalam format 'Mar-2025' 
    menjadi list ['MAR', 2025].
    """
    from datetime import datetime
    
    try:
        # Coba konversi string menjadi datetime dengan format '%b-%Y'
        # %b = nama bulan singkat (Mar, Apr, dst), %Y = tahun 4 digit
        dt = datetime.strptime(value, '%b-%Y')
        
        # Mengembalikan dalam format ['MAR', 2025]
        return [dt.strftime('%b').upper(), dt.year]
    
    except ValueError:
        # Jika format tidak sesuai, lemparkan error validasi
        raise ValueError('Format periode harus seperti Mar-2025.')
    
def validate_date_range(start_date: str, finish_date: str, context: str = "Data") -> None:
    """
    Validates that a start date is not after a finish date.
    Raises an Exception if the validation fails.
    """
    # If either date is missing (None or empty string), there's nothing to compare
    if not start_date or not finish_date:
        return 

    try:
        # Parse standard HTML5 date input format (YYYY-MM-DD)
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date() if isinstance(start_date, str) else start_date
        finish_dt = datetime.strptime(finish_date, '%Y-%m-%d').date() if isinstance(finish_date, str) else finish_date
        
        if start_dt > finish_dt:
            raise Exception(f"Tanggal mulai tidak boleh lebih dari tanggal selesai untuk {context}.")
            
    except ValueError as e:
        # This catches bad formats or impossible dates (like Feb 30th)
        if "does not match format" in str(e) or "day is out of range" in str(e):
            raise Exception(f"Format tanggal tidak valid pada {context}.")
        else:
            raise e # Re-raise if it's our custom validation exception