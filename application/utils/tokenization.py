# sr_transaction.py
from itsdangerous import URLSafeSerializer
from flask import current_app

def encrypt_id(sr_no: str) -> str:
    # Uses your Flask app's SECRET_KEY to create a secure lock
    s = URLSafeSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(sr_no)

def decrypt_token(token: str):
    s = URLSafeSerializer(current_app.config['SECRET_KEY'])
    try:
        return s.loads(token)
    except Exception:
        # If a hacker tampers with the token, it fails safely
        return None