import requests
from flask import session
from common.midiconnectserver.midilog import Logger

Log = Logger()


def _set_role_session(nik: str) -> tuple:
    """
    Phase 2 login: query sr_user untuk cek apakah NIK terdaftar,
    lalu ambil role dan permissions-nya dari DB.
    - Jika NIK tidak terdaftar di sr_user → permissions kosong, tetap sukses.
    - Jika DB error → return (False, pesan error).
    Return: (bool sukses, str|None pesan error)
    """
    from application.transactions.auth_transaction import get_user_role_info_trx
    role_info = get_user_role_info_trx(nik)

    if role_info.get('error'):
        Log.error(f"LOGIN | Phase 2 FAILED | NIK: {nik} | DB error saat mengambil role/permission")
        return False, 'Terjadi kesalahan sistem saat verifikasi hak akses. Silakan coba lagi.'

    session['role'] = {
        'name': role_info.get('name', []),
        'permissions': role_info.get('permissions', [])
    }
    Log.info(f"LOGIN | Phase 2 OK | NIK: {nik} | Role: {', '.join(role_info.get('name', []))} | Permissions: {role_info.get('permissions', [])}")
    return True, None


def _finalize_login(nik: str, log_label: str) -> tuple:
    """Helper: jalankan Phase 2, rollback session jika gagal."""
    ok, err = _set_role_session(nik)
    if not ok:
        session.clear()
        return None, err
    Log.info(f"LOGIN | {log_label} | NIK: {nik}")
    return 'T', None


def validate_user_gateway(nik, password):
    app_name = 'OWH'
    try:
        # Data Dummy
        if nik == '123' and password == '123':
            session['user'] = {
                'nik': '1234567890',
                'nama': 'Developer User',
                'jabatan': 'IT Programmer',
                'toko': 'T000',
                'nm_toko': 'Head Office',
                'divisi': 'IT Development',
                'email': 'dev@midiconnect.com',
                'branch': 'HO'
            }
            return _finalize_login('1234567890', 'DUMMY USER LOGIN SUCCESS')

        if nik == '00000' and password == 'admin123':
            session['user'] = {
                'nik': '00000',
                'nama': 'Administrator',
                'jabatan': 'IT Programmer',
                'toko': 'T000',
                'nm_toko': 'Head Office',
                'divisi': 'IT Development',
                'email': 'dev@midiconnect.com',
                'branch': 'HO'
            }
            return _finalize_login('00000', 'DUMMY USER LOGIN SUCCESS')

        _test_accounts = {
            # NIK: (password, nama, jabatan)
            '02000000':   ('magang123',  'MAGANG IT',                    'IT PMO'),
            '0201080005': ('gm123',      'IT GENERAL MANAGER',           'IT General Manager'),
            '0214083545': ('pm123',      'GALIH AGUSFIAN PERMANA',       'IT Project Manager'),
            '0201080008': ('sm123',      'IT SM DW',                     'IT Senior Manager'),
            '0208010095': ('sm123',      'IT SM BS',                     'IT Senior Manager'),
            '0208080011': ('sm123',      'IT SM OPS',                    'IT Senior Manager'),
            '0219096129': ('scm123',     'NOVRI RISKY PATALALA',         'It Back Office Development Analyst'),
            '0200000000': ('dev123',     'DUMMY',                        'It Back Office Development Analyst'),
            '0222108168': ('ro123',      'ALFANI ZIDNI HIDAYAH',         'It Office Support'),
        }

        if nik in _test_accounts and password == _test_accounts[nik][0]:
            acct = _test_accounts[nik]
            session['user'] = {
                'nik': nik,
                'nama': acct[1],
                'jabatan': acct[2],
                'toko': 'SZ01',
                'nm_toko': 'Head Office',
                'divisi': 'IT Development',
                'email': f'{nik}@test.com',
                'branch': 'HO'
            }
            return _finalize_login(nik, f'TEST ACCOUNT LOGIN | NIK: {nik}')

        # Midigateway
        URL = "https://hoapimac.mu.co.id/ceklogin"
        response = requests.post(URL, json={'xnik': nik, 'xpin': password, 'xapl': app_name})

        if response.status_code == 200:
            data = response.json()

            if data[0].get('sukses') == 'T':
                user_data = data[0]
                session['user'] = {
                    'nik': user_data['nik'],
                    'nama': user_data['nama'],
                    'jabatan': user_data['jabatan'],
                    'toko': user_data['toko'],
                    'nm_toko': user_data['nm_toko'],
                    'divisi': user_data['divisi'],
                    'email': user_data['email'],
                    'branch': user_data['branch']
                }
                return _finalize_login(user_data['nik'], f'MIDIGATEWAY LOGIN SUCCESS | NIK: {user_data["nik"]}')
            else:
                return None, 'NIK dan PIN Tidak Sesuai!'
        else:
            return None, 'NIK dan PIN Tidak Sesuai!'

    except requests.RequestException as e:
        Log.error(f"LOGIN | Request error: {str(e)}")
        return None, 'Terjadi kesalahan pada server. Silakan coba lagi nanti.'

    except Exception as e:
        Log.error(f"LOGIN | Unexpected error: {str(e)}")
        return None, 'Terjadi kesalahan yang tidak terduga. Silakan coba lagi nanti.'
