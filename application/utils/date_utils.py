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