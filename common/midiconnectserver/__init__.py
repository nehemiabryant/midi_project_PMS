"""
MIDI Connect Server

Features:
- Secure config reader supporting Fernet-encrypted configs via env/file key
- Backward-compatible fallback to ordinal-encoded Connection.cfg
- Structured, user-friendly error objects (incl. tablespace/space and network hints)
- Uniform return schema across DBs
"""

import os
import json
import traceback
from typing import Any, Dict, Tuple, Optional

from cryptography.fernet import Fernet, InvalidToken

import psycopg2
import psycopg2.errors
import oracledb as cx_Oracle

try:
    # Use local-only logger
    from common.midiconnectserver.midilog import Logger
except Exception:  # pragma: no cover
    from .midilog import Logger  # type: ignore


Log = Logger()


class SecureConfig:
    """
    Load DB connection config securely.

    Precedence:
    1) Encrypted JSON config path via env MIDI_SECURE_CFG (Fernet token per file content)
       - Key from env MIDI_DB_KEY (base64 urlsafe), or file path MIDI_DB_KEY_PATH
    2) Fallback to legacy ordinal-encoded Connection.cfg using decoder from older module
       - Searches config/Connection.cfg
    """

    def __init__(self):
        self._fernet = self._build_fernet()

    def _build_fernet(self) -> Optional[Fernet]:
        key = os.environ.get("MIDI_DB_KEY", "").strip()
        key_path = os.environ.get("MIDI_DB_KEY_PATH", "").strip()
        if not key and key_path and os.path.exists(key_path):
            try:
                with open(key_path, "rb") as fh:
                    key = fh.read().strip().decode("utf-8")
            except Exception as exc:
                Log.error(f"Failed reading key from path: {exc}")
        if key:
            try:
                return Fernet(key.encode("utf-8"))
            except Exception as exc:
                Log.error(f"Invalid MIDI_DB_KEY: {exc}")
        return None

    def _load_encrypted_json(self) -> Optional[Dict[str, Any]]:
        cfg_path = os.environ.get("MIDI_SECURE_CFG", "").strip()
        if not cfg_path:
            return None
        if not self._fernet:
            Log.error("MIDI_SECURE_CFG provided but no MIDI_DB_KEY/MIDI_DB_KEY_PATH available")
            return None
        try:
            with open(cfg_path, "rb") as fh:
                token = fh.read()
            decrypted = self._fernet.decrypt(token)
            payload = json.loads(decrypted.decode("utf-8"))
            # Expected structure: {"ALIA S": {host, port, databaseName, username, password, schema}}
            return {k.upper(): v for k, v in payload.items()}
        except (InvalidToken, json.JSONDecodeError) as exc:
            Log.error(f"Failed to decrypt/parse secure config: {exc}")
        except Exception as exc:
            Log.error(f"Error reading secure config: {exc}")
        return None

    def _decoder_ordinal(self, parts: Any) -> Any:
        # Copied logic from legacy module, minimized dependency
        result = []
        for datum in parts:
            temp = ""
            for x in str(datum).strip().split("+"):
                if x:
                    try:
                        temp += chr(int(x))
                    except Exception:
                        pass
            result.append(temp)
        return result

    def _load_legacy_cfg(self) -> Dict[str, Dict[str, str]]:
        # Only use the config in common/midiconnectserver/config/Connection.cfg
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "Connection.cfg")
        cfg: Dict[str, Dict[str, str]] = {}
        tried_paths = [path]
        try:
            if not os.path.exists(path):
                Log.error(f"Tidak ada file Connection.cfg ditemukan. Path yang dicoba: {tried_paths}")
                return cfg
            with open(path, "r") as stream:
                content = stream.read()
            # detect SECRET_KEY line if present
            key_val = None
            for line in content.split("\n"):
                l = line.strip()
                if not l:
                    continue
                if l.startswith("#"):
                    continue
                if l.upper().startswith("SECRET_KEY="):
                    key_val = l.split("=", 1)[1].strip()
                    break
            # Try token-based entries first if we have a key or env-based fernet
            fernet_obj = None
            if self._fernet:
                fernet_obj = self._fernet
            elif key_val:
                try:
                    fernet_obj = Fernet(key_val.encode("utf-8"))
                except Exception as exc:
                    Log.error(f"Invalid SECRET_KEY in {path}: {exc}")
            if fernet_obj is not None:
                for line in content.split("\n"):
                    l = line.strip()
                    if not l or l.startswith("#") or l.upper().startswith("SECRET_KEY="):
                        continue
                    # expected format: ALIAS <token>
                    parts = l.split(" ", 1)
                    if len(parts) != 2:
                        continue
                    alias_u, token = parts[0].upper(), parts[1].strip()
                    try:
                        decrypted = fernet_obj.decrypt(token.encode("utf-8")).decode("utf-8")
                        obj = json.loads(decrypted)
                        host = obj.get("host")
                        if os.environ.get("GAE_ENV") == "standard" or os.environ.get("CLOUD_APPS") == "CLOUD_RUN":
                            if ":" in host:
                                host = f"/cloudsql/{host}"
                        cfg[alias_u] = {
                            "databaseName": str(obj.get("databaseName")).lower(),
                            "host": host,
                            "username": str(obj.get("username")).lower(),
                            "password": obj.get("password"),
                            "port": str(obj.get("port")),
                            "schema": str(obj.get("schema", "public")).lower(),
                        }
                    except Exception:
                        continue
        except Exception as exc:
            Log.error(f"Error reading legacy config {path}: {exc}")
        if not cfg:
            Log.error(f"Tidak ada alias ditemukan di file Connection.cfg. Path yang dicoba: {tried_paths}")
        return cfg

    def get(self, alias: str) -> Tuple[bool, Dict[str, str]]:
        alias_u = alias.upper()
        payload = self._load_encrypted_json()
        if payload and alias_u in payload:
            try:
                v = payload[alias_u]
                return True, {
                    "databaseName": str(v["databaseName"]).lower(),
                    "host": v["host"],
                    "username": str(v["username"]).lower(),
                    "password": v["password"],
                    "port": str(v["port"]),
                    "schema": str(v.get("schema", "public")).lower(),
                }
            except Exception as exc:
                Log.error(f"Malformed secure config for {alias_u}: {exc}")
        legacy = self._load_legacy_cfg()
        v2 = legacy.get(alias_u)
        if v2:
            return True, v2
        return False, {}


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
        "errormsg": msg.split("\n")[0],
        "errorclass": e.__class__.__name__,
        "hint": hint,
        "query": query,
    }


def _normalize_error_ora(e: Exception, query: str = "") -> Dict[str, Any]:
    msg = str(e)
    code = "ORA"
    if isinstance(e, cx_Oracle.Error):
        try:
            err, = e.args
            msg = str(err)
            code = getattr(err, "code", code)
        except Exception:
            pass
    hint = ""
    low = msg.lower()
    if "tablespace" in low or "no space" in low or "unable to extend" in low:
        hint = "Periksa tablespace/segment. Minta DBA extend tablespace."
    elif "timeout" in low or "session" in low and "killed" in low:
        hint = "Cek jaringan, resource limit, dan parameter timeout."
    return {
        "errorcode": code,
        "msg": msg,
        "errormsg": msg.split("\n")[0],
        "errorclass": e.__class__.__name__,
        "hint": hint,
        "query": query,
    }


class DatabasePG:
    def __init__(self, alias: str, autocommit: bool = False):
        self._alias = alias
        self.status = {"status": False, "msg": "", "errorcode": ""}
        self._conn = None
        self._curs = None
        self._connect(autocommit)

    def _connect(self, autocommit: bool):
        try:
            ok, cfg = SecureConfig().get(self._alias)
            if not ok:
                self.status = {"status": False, "msg": "File konfigurasi tidak ditemukan", "errorcode": "CFGNF"}
                return
            dsn = (
                "host='{host}' port='{port}' dbname='{dbname}' user='{user}' password='{password}'"
                .format(
                    host=cfg.get("host", "127.0.0.1"),
                    port=cfg.get("port", "5432"),
                    dbname=cfg.get("databaseName"),
                    user=cfg.get("username"),
                    password=cfg.get("password"),
                )
            )
            self._conn = psycopg2.connect(dsn)
            self._conn.autocommit = autocommit
            self._curs = self._conn.cursor()
            self.status = {"status": True, "msg": "Koneksi Database Postgres Berhasil", "errorcode": "00"}
        except psycopg2.Error as e:
            Log.error(message=e)
            self.status = {"status": False, "msg": "Koneksi Database Error", "errorcode": getattr(e, "pgcode", "01") or "01"}
        except Exception as e:
            Log.error(message=e)
            self.status = {"status": False, "msg": "Error Konfigurasi Database", "errorcode": "02"}

    def _wrap(self, fn, *args, query: str = "", notices: bool = True):
        res = _result_template()
        if not self.status.get("status") or self._curs is None or self._conn is None:
            return self.status
        try:
            fn(*args)
            if hasattr(self._curs, "fetchall") and query:
                pass
            if notices and hasattr(self._conn, "notices"):
                res["notices"] = self._conn.notices
            res["rowcount"] = getattr(self._curs, "rowcount", "")
            res["status"] = True
            res["msg"] = "statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_pg(e, query)
            Log.error(message=f"PG ERROR: {err}")
            res.update(err)
        return res

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
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_pg(e, select_string)
            Log.error(message=f"PG ERROR: {err}")
            res.update(err)
        return res

    def selectData(self, select_string: str, param: Any, rownum: str = "ALL"):
        res = _result_template()
        if not self.status.get("status") or self._curs is None or self._conn is None:
            return self.status
        try:
            self._curs.execute(select_string, param)
            if rownum == "ALL":
                data = self._curs.fetchall()
            else:
                data = self._curs.fetchmany(int(rownum))
            res["data"] = data
            res["notices"] = self._conn.notices
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "select statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_pg(e, select_string)
            Log.error(message=f"PG ERROR: {err}")
            res.update(err)
        return res

    def selectHeader(self, select_string: str):
        res = _result_template()
        if not self.status.get("status") or self._curs is None or self._conn is None:
            return self.status
        try:
            self._curs.execute(select_string)
            if self._curs.description is not None:
                header = [col[0] for col in self._curs.description]
            else:
                header = []
            dataTemp = self._curs.fetchall()
            res["data"] = [header, dataTemp]
            res["notices"] = self._conn.notices
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "select statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_pg(e, select_string)
            Log.error(message=f"PG ERROR: {err}")
            res.update(err)
        return res

    def selectDataHeader(self, select_string: str, param: Any):
        res = _result_template()
        if not self.status.get("status") or self._curs is None or self._conn is None:
            return self.status
        try:
            self._curs.execute(select_string, param)
            if self._curs.description is not None:
                header = [col[0] for col in self._curs.description]
            else:
                header = []
            dataTemp = self._curs.fetchall()
            res["data"] = [header, dataTemp]
            res["notices"] = self._conn.notices
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "select statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_pg(e, select_string)
            Log.error(message=f"PG ERROR: {err}")
            res.update(err)
        return res

    def execute(self, exec_string: str):
        res = _result_template()
        if not self.status.get("status") or self._curs is None or self._conn is None:
            return self.status
        try:
            self._curs.execute(exec_string)
            self._curs.execute("commit")
            res["notices"] = self._conn.notices
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "execute statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_pg(e, exec_string)
            Log.error(message=f"PG ERROR: {err}")
            res.update(err)
        return res

    def executeData(self, exec_string: str, param: Any):
        res = _result_template()
        if not self.status.get("status") or self._curs is None or self._conn is None:
            return self.status
        try:
            self._curs.execute(exec_string, param)
            self._curs.execute("commit")
            res["notices"] = self._conn.notices
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "execute statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_pg(e, exec_string)
            Log.error(message=f"PG ERROR: {err}")
            res.update(err)
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
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_pg(e, exec_string)
            Log.error(message=f"PG ERROR: {err}")
            res.update(err)
        return res

    def executeMany(self, exec_string: str, param: Any):
        res = _result_template()
        if not self.status.get("status") or self._curs is None or self._conn is None:
            return self.status
        try:
            self._curs.executemany(exec_string, param)
            self._curs.execute("commit")
            res["notices"] = self._conn.notices
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "executemany statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_pg(e, exec_string)
            Log.error(message=f"PG ERROR: {err}")
            res.update(err)
        return res

    def executePro(self, exec_string: str, param: Any):
        # callproc wrapper
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
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_pg(e, exec_string)
            Log.error(message=f"PG ERROR: {err}")
            res.update(err)
        return res

    def close(self):
        res = _result_template()
        if not self.status.get("status") or self._conn is None:
            return self.status
        try:
            self._conn.close()
            res["status"] = True
            res["msg"] = "Berhasil Menutup Koneksi"
            res["errorcode"] = "0"
        except Exception as e:
            err = _normalize_error_pg(e, "Delete Connection")
            Log.error(message=f"PG ERROR: {err}")
            res.update(err)
        return res


class DatabaseORA:
    def __init__(self, alias: str, autocommit: bool = False):
        self._alias = alias
        self.status = {"status": False, "msg": "", "errorcode": ""}
        self._conn = None
        self._curs = None
        self._connect(autocommit)

    def _connect(self, autocommit: bool):
        ok, cfg = SecureConfig().get(self._alias)
        if not ok:
            self.status = {"status": False, "msg": "File konfigurasi tidak ditemukan", "errorcode": "CFGNF"}
            return
        try:
            host = cfg.get("host", "127.0.0.1")
            port = cfg.get("port", "1521")
            dbname = cfg.get("databaseName")
            username = cfg.get("username")
            password = cfg.get("password")
            dsn = f"{host}:{port}/{dbname}"
            self._conn = cx_Oracle.connect(username, password, dsn)
            # cx_Oracle default autocommit False; retain behavior
            self._curs = self._conn.cursor()
            self.status = {"status": True, "msg": "Koneksi Database Oracle Berhasil", "errorcode": "00"}
        except cx_Oracle.Error as e:
            Log.error(message=e)
            self.status = {"status": False, "msg": "Koneksi Database Error", "errorcode": "01"}
        except Exception as e:
            Log.error(message=e)
            self.status = {"status": False, "msg": "Error Konfigurasi Database", "errorcode": "02"}

    def select(self, select_string: str):
        res = _result_template()
        if not self.status.get("status") or self._curs is None:
            return self.status
        try:
            self._curs.execute(select_string)
            res["data"] = self._curs.fetchall()
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "select statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_ora(e, select_string)
            Log.error(message=f"ORA ERROR: {err}")
            res.update(err)
        return res

    def selectData(self, select_string: str, param: Any, rownum: str = "ALL"):
        res = _result_template()
        if not self.status.get("status") or self._curs is None:
            return self.status
        try:
            self._curs.execute(select_string, param)
            if rownum == "ALL":
                data = self._curs.fetchall()
            else:
                data = self._curs.fetchmany(int(rownum))
            res["data"] = data
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "select statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_ora(e, select_string)
            Log.error(message=f"ORA ERROR: {err}")
            res.update(err)
        return res

    def selectHeader(self, select_string: str):
        res = _result_template()
        if not self.status.get("status") or self._curs is None:
            return self.status
        try:
            self._curs.execute(select_string)
            if self._curs.description is not None:
                header = [col[0] for col in self._curs.description]
            else:
                header = []
            res["data"] = [header, self._curs.fetchall()]
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "select statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_ora(e, select_string)
            Log.error(message=f"ORA ERROR: {err}")
            res.update(err)
        return res

    def selectDataHeader(self, select_string: str, param: Any):
        res = _result_template()
        if not self.status.get("status") or self._curs is None:
            return self.status
        try:
            self._curs.execute(select_string, param)
            if self._curs.description is not None:
                header = [col[0] for col in self._curs.description]
            else:
                header = []
            res["data"] = [header, self._curs.fetchall()]
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "select statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_ora(e, select_string)
            Log.error(message=f"ORA ERROR: {err}")
            res.update(err)
        return res

    def execute(self, exec_string: str):
        res = _result_template()
        if not self.status.get("status") or self._curs is None:
            return self.status
        try:
            self._curs.execute(exec_string)
            self._curs.execute("commit")
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "execute statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_ora(e, exec_string)
            Log.error(message=f"ORA ERROR: {err}")
            res.update(err)
        return res

    def executeData(self, exec_string: str, param: Any):
        res = _result_template()
        if not self.status.get("status") or self._curs is None:
            return self.status
        try:
            self._curs.execute(exec_string, param)
            self._curs.execute("commit")
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "execute statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_ora(e, exec_string)
            Log.error(message=f"ORA ERROR: {err}")
            res.update(err)
        return res

    def executePro(self, exec_string: str, param: Any):
        res = _result_template()
        if not self.status.get("status") or self._curs is None:
            return self.status
        try:
            self._curs.callproc(exec_string, param)
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "executePro statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_ora(e, exec_string)
            Log.error(message=f"ORA ERROR: {err}")
            res.update(err)
        return res

    def executeMany(self, exec_string: str, param: Any):
        res = _result_template()
        if not self.status.get("status") or self._curs is None:
            return self.status
        try:
            self._curs.executemany(exec_string, param)
            self._curs.execute("commit")
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "executemany statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_ora(e, exec_string)
            Log.error(message=f"ORA ERROR: {err}")
            res.update(err)
        return res

    def executeFunc(self, exec_string: str, paramString: Any):
        res = _result_template()
        if not self.status.get("status") or self._curs is None:
            return self.status
        try:
            myVar = self._curs.var(cx_Oracle.STRING)
            vResult = self._curs.callfunc(exec_string, myVar, paramString)
            res["data"] = vResult
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "executeFunc statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_ora(e, exec_string)
            Log.error(message=f"ORA ERROR: {err}")
            res.update(err)
        return res

    def executeDataNoCommit(self, exec_string: str, param: Any):
        res = _result_template()
        if not self.status.get("status") or self._curs is None:
            return self.status
        try:
            self._curs.execute(exec_string, param)
            res["rowcount"] = self._curs.rowcount
            res["status"] = True
            res["msg"] = "execute statement berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            try:
                if self._curs is not None:
                    self._curs.execute("rollback")
            except Exception:
                pass
            err = _normalize_error_ora(e, exec_string)
            Log.error(message=f"ORA ERROR: {err}")
            res.update(err)
        return res

    def forCommit(self):
        res = _result_template()
        if not self.status.get("status") or self._conn is None:
            return self.status
        try:
            self._conn.commit()
            res["status"] = True
            res["msg"] = "commit berhasil"
            res["errorcode"] = "0"
        except Exception as e:
            err = _normalize_error_ora(e, "commit")
            Log.error(message=f"ORA ERROR: {err}")
            res.update(err)
        return res

    def close(self):
        res = _result_template()
        if not self.status.get("status") or self._conn is None:
            return self.status
        try:
            self._conn.close()
            res["status"] = True
            res["msg"] = "Berhasil Menutup Koneksi"
            res["errorcode"] = "0"
        except Exception as e:
            err = _normalize_error_ora(e, "Delete Connection")
            Log.error(message=f"ORA ERROR: {err}")
            res.update(err)
        return res