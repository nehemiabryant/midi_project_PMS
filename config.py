production = False
# production = True

# Main Configuration
class MainConfig:
    if production == True:
        DEBUG = False
        HOST = ''
        PORT = 3300
        CORS_HOST = [
            'http://10.4.24.26'
        ]
    else:
        DEBUG = True
        HOST = '127.0.0.1'
        PORT = 3300
        CORS_HOST = ['http://127.0.0.1']

    # Link Host
    HOST_URL = f'http://{HOST}:{PORT}'