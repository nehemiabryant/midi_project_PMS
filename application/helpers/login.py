import re, requests
from flask import current_app as app, session
from common.midiconnectserver.midilog import Logger

Log = Logger()

def validate_user_gateway(nik, password):
    app_name = 'OWH'
    try:
        if nik == '123' and password == '123':
        # Data Dummy
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

            session['role'] = {
                'name': "Administrator",
                'level': 1
            }

            Log.info("LOGIN | DUMMY USER LOGIN SUCCESS")
            return 'T', None
        
        # if not re.match(r'^\d{10}$', nik):
        #     return None, 'Format NIK Tidak Sesuai!'

        # Midigateway
        URL = "https://hoapimac.mu.co.id/ceklogin"
        response = requests.post(URL, json={'xnik': nik, 'xpin': password, 'xapl':app_name})
        
        if response.status_code == 200:
            data = response.json()
            # Log.info(f"LOGIN | API Response Data: {data}")

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

                session['role'] = {
                    'name': "",
                    'level': 0
                }

                # Final
                return 'T', None
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