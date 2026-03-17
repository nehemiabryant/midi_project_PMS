import traceback, pandas as pd
from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

def get_workflow_rule(current_smk_id: int, next_smk_id: int) -> dict:
    sql = """
        SELECT rule_id, allowed_picrole
        FROM public.sr_ms_workflow_rules
        WHERE current_smk_id = %(current_smk_id)s AND next_smk_id = %(next_smk_id)s
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if conn:
            return conn.selectData(sql, {'current_smk_id': current_smk_id, 'next_smk_id': next_smk_id})
        return {'status': False, 'msg': 'DB Connection failed'}
    except Exception as e:
        Log.error(f'Exception | get_workflow_rule | Msg: {str(e)}')
        return {'status': False, 'msg': str(e)}
    finally:
        if conn: conn.close()

def get_mandatory_docs(rule_id: int) -> dict:
    sql = """
        SELECT attach_ctg
        FROM public.sr_mandatory_docs
        WHERE rule_id = %(rule_id)s
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if conn:
            return conn.selectData(sql, {'rule_id': rule_id})
        return {'status': False, 'msg': 'DB Connection failed'}
    except Exception as e:
        Log.error(f'Exception | get_mandatory_docs | Msg: {str(e)}')
        return {'status': False, 'msg': str(e)}
    finally:
        if conn: conn.close()

def get_uploaded_docs(sr_no: str) -> dict:
    sql = """
        SELECT DISTINCT attach_ctg
        FROM public.sr_attachment
        WHERE sr_no = %(sr_no)s
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if conn:
            return conn.selectData(sql, {'sr_no': sr_no})
        return {'status': False, 'msg': 'DB Connection failed'}
    except Exception as e:
        Log.error(f'Exception | get_uploaded_docs | Msg: {str(e)}')
        return {'status': False, 'msg': str(e)}
    finally:
        if conn: conn.close()