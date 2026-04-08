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
    return wib_dt.strftime('%d %b %Y %H:%M') + ' WIB'


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