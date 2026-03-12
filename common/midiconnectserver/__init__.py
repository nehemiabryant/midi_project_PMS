import os
import psycopg2
from typing import Any, Dict

try:
    # Use local-only logger
    from common.midiconnectserver.midilog import Logger
except Exception:  # pragma: no cover
    from .midilog import Logger  # type: ignore


Log = Logger()

# --- HELPER FUNCTIONS ---
def _result_template() -> Dict[str, Any]:
    return {
        "status": False,
        "data": "",
        "msg": "",
        "notices": "",
        "rowcount": "",
        "errorcode": "",
        "errormsg": "",
        "errorclass": "",
        "hint": "",
    }

def _normalize_error_pg(e: Exception, query: str = "") -> Dict[str, Any]:
    msg = str(getattr(e, "pgerror", "") or str(e))
    code = getattr(e, "pgcode", "") or "PGERR"
    hint = ""
    low = msg.lower()
    
    if "tablespace" in low or "no space" in low or "disk quota" in low:
        hint = "Periksa tablespace/disk space. Hubungi DBA bila penuh."
    elif "timeout" in low or "closed the connection" in low:
        hint = "Cek network/VPN, parameter statement_timeout, dan konektivitas DB."
        
    return {
        "errorcode": code,
        "msg": msg,
        "errormsg": msg.split("\n")[0] if msg else "",
        "errorclass": e.__class__.__name__,
        "hint": hint,
        "query": query,
    }

# --- DATABASE CLASS ---
class DatabasePG:
    def __init__(self, alias: str, autocommit: bool = False):
        self._alias = alias
        self.status = _result_template()
        self._conn = None
        self._curs = None
        self._connect(autocommit)

    def _get_credentials_from_cfg(self, alias_target: str) -> str:
        """Parses the cfg file to find the connection string for the alias."""
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "Connection.cfg")
        if not os.path.exists(cfg_path):
            raise Exception(f"Config file '{cfg_path}' not found.")
            
        with open(cfg_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                parts = line.split(None, 1)
                if len(parts) == 2:
                    alias_name, credentials = parts
                    if alias_name == alias_target:
                        return credentials
        return ""

    def _connect(self, autocommit: bool):
        try:
            conn_string = self._get_credentials_from_cfg(self._alias)
            if not conn_string:
                raise Exception(f"Alias '{self._alias}' not found in db.cfg.")

            self._conn = psycopg2.connect(conn_string)
            self._conn.autocommit = autocommit
            self._curs = self._conn.cursor()
            
            self.status["status"] = True
            self.status["msg"] = "Koneksi Berhasil"
            self.status["errorcode"] = "0"
            
        except Exception as e:
            err = _normalize_error_pg(e, f"Connect to {self._alias}")
            self.status.update(err)
            Log.error(f"DB Connect Error ({self._alias}): {self.status['msg']}")

    def _handle_error(self, e: Exception, sql_string: str, res: Dict[str, Any]) -> Dict[str, Any]:
        """Centralized error handler and rollback executor."""
        try:
            if self._conn and not self._conn.autocommit:
                self._conn.rollback()
        except Exception:
            pass
        err = _normalize_error_pg(e, sql_string)
        Log.error(message=f"PG ERROR: {err}")
        res.update(err)
        return res

    # --- SELECT METHODS ---

    def select(self, select_string: str):
        res = _result_template()
        if not self.status.get("status") or self._curs is None or self._conn is None:
            return self.status
        try:
            self._curs.execute(select_string)
            res["data"] = self._curs.fetchall()
            res["notices"] = self._conn.notices
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "select statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            res = self._handle_error(e, select_string, res)
        return res

    def selectData(self, select_string: str, param: Any, rownum: str = "ALL"):
        res = _result_template()
        if not self.status.get("status") or self._curs is None or self._conn is None:
            return self.status
        try:
            self._curs.execute(select_string, param)
            if rownum == "ALL":
                res["data"] = self._curs.fetchall()
            else:
                res["data"] = self._curs.fetchmany(int(rownum))
            res["notices"] = self._conn.notices
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "select statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            res = self._handle_error(e, select_string, res)
        return res

    def selectHeader(self, select_string: str):
        res = _result_template()
        if not self.status.get("status") or self._curs is None or self._conn is None:
            return self.status
        try:
            self._curs.execute(select_string)
            header = [col[0] for col in self._curs.description] if self._curs.description else []
            dataTemp = self._curs.fetchall()
            res["data"] = [header, dataTemp]
            res["notices"] = self._conn.notices
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "select statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            res = self._handle_error(e, select_string, res)
        return res

    def selectDataHeader(self, select_string: str, param: Any):
        res = _result_template()
        if not self.status.get("status") or self._curs is None or self._conn is None:
            return self.status
        try:
            self._curs.execute(select_string, param)
            header = [col[0] for col in self._curs.description] if self._curs.description else []
            dataTemp = self._curs.fetchall()
            res["data"] = [header, dataTemp]
            res["notices"] = self._conn.notices
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "select statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            res = self._handle_error(e, select_string, res)
        return res

    # --- EXECUTE METHODS ---

    def execute(self, exec_string: str):
        res = _result_template()
        if not self.status.get("status") or self._curs is None or self._conn is None:
            return self.status
        try:
            self._curs.execute(exec_string)
            if not self._conn.autocommit:
                self._conn.commit()
            res["notices"] = self._conn.notices
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "execute statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            res = self._handle_error(e, exec_string, res)
        return res

    def executeData(self, exec_string: str, param: Any):
        res = _result_template()
        if not self.status.get("status") or self._curs is None or self._conn is None:
            return self.status
        try:
            self._curs.execute(exec_string, param)
            if not self._conn.autocommit:
                self._conn.commit()
            res["notices"] = self._conn.notices
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "execute statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            res = self._handle_error(e, exec_string, res)
        return res

    def executeDataNoCommit(self, exec_string: str, param: Any):
        res = _result_template()
        if not self.status.get("status") or self._curs is None or self._conn is None:
            return self.status
        try:
            self._curs.execute(exec_string, param)
            res["notices"] = self._conn.notices
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "execute statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            res = self._handle_error(e, exec_string, res)
        return res

    def executeMany(self, exec_string: str, param: Any):
        res = _result_template()
        if not self.status.get("status") or self._curs is None or self._conn is None:
            return self.status
        try:
            self._curs.executemany(exec_string, param)
            if not self._conn.autocommit:
                self._conn.commit()
            res["notices"] = self._conn.notices
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "executemany statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            res = self._handle_error(e, exec_string, res)
        return res

    def executePro(self, exec_string: str, param: Any):
        res = _result_template()
        if not self.status.get("status") or self._curs is None or self._conn is None:
            return self.status
        try:
            self._curs.callproc(exec_string, param)
            res["notices"] = self._conn.notices
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "executePro statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            res = self._handle_error(e, exec_string, res)
        return res

    def close(self):
        res = _result_template()
        if not self.status.get("status") or self._conn is None:
            return self.status
        try:
            if self._curs:
                self._curs.close()
            self._conn.close()
            res["status"] = True
            res["msg"] = "Berhasil Menutup Koneksi"
            res["errorcode"] = "0"
        except Exception as e:
            err = _normalize_error_pg(e, "Delete Connection")
            Log.error(message=f"PG ERROR: {err}")
            res.update(err)
        return res