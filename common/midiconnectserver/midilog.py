from datetime import datetime
import os
from pathlib import Path


class Logger:
    """
    Simple local file logger. Writes logs to ./log/YYYY-MM-DD.txt
    Usage:
        Log = Logger()
        Log.info("message")
    Methods: debug, info, warning, error, critical
    """

    def __init__(self, log_dir: str = '', log_name: str = ''):
        self.__logger = ""
        self.__log_dir = log_dir or f"{os.getcwd()}/log"
        self.__file_name = log_name  # optional explicit file name
        self.createLogger()

    def createLogger(self):
        Path(self.__log_dir).mkdir(parents=True, exist_ok=True)
        if self.__file_name:
            self.__logger = os.path.join(self.__log_dir, self.__file_name)
        else:
            self.__logger = f"{self.__log_dir}/{datetime.now().strftime('%Y-%m-%d')}.txt"

    def __logStruct(self, severity, msg):
        fileOpen = open(self.__logger, "a")
        dictParam = f"{severity} | {datetime.now().strftime('%Y-%m-%d')} | {datetime.now().strftime('%H:%M:%S')} | {msg}"
        fileOpen.write(f"{str(dictParam)}\n")
        fileOpen.close()

    def debug(self, message):
        self.__logStruct(severity="DEBUG", msg=message)

    def info(self, message):
        self.__logStruct(severity="INFO", msg=message)

    def warning(self, message):
        self.__logStruct(severity="WARNING", msg=message)

    def error(self, message):
        self.__logStruct(severity="ERROR", msg=message)

    def critical(self, message):
        self.__logStruct(severity="CRITICAL", msg=message)