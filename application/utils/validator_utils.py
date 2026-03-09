def validate_required_fields(data, required_fields):
    """Cek semua key wajib ada dan tidak kosong."""
    for field in required_fields:
        if not data.get(field):
            return False
    return True

def validate_email_format(email):
    """Cek format email sederhana."""
    if not email:
        return False
    if "@" not in email or "." not in email:
        return False
    return True

def validate_email_regex(email):
    """Validate email format using regex for more comprehensive checking."""
    import re
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email)) if email else False

def validate_period(form, field):
    from datetime import datetime
    from wtforms.validators import ValidationError

    try:
        datetime.strptime(field.data, '%b-%Y')  # %b = nama bulan singkat, %Y = tahun 4 digit
        # field.data = period  # Menyimpan objek datetime
    except ValueError:
        raise ValidationError('Format tanggal harus seperti Jan-2025.')