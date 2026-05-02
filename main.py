import logging
from application import create_app
from config import MainConfig
from datetime import timedelta

# Suppress Flask/Werkzeug request logs to terminal
class NoRequestLogFilter(logging.Filter):
    def filter(self, record):
        return False

logging.getLogger('werkzeug').addFilter(NoRequestLogFilter())

app = create_app()
app.config['SESSION_TYPE'] = 'filesystem'
app.permanent_session_lifetime = timedelta(hours=1)

if __name__ == '__main__':
    print(f"\033[91mServer running at http://{MainConfig.HOST}:{MainConfig.PORT}\033[0m\n")
    app.run(host=MainConfig.HOST, port=MainConfig.PORT, debug=MainConfig.DEBUG)
