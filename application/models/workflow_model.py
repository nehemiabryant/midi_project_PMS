import traceback, pandas as pd
from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

def get_workflow_rule(current_smk_id: int, next_smk_id: int, shared_conn=None) -> dict:
    sql = """
        SELECT rule_id, allowed_picrole
        FROM public.sr_ms_workflow_rules
        WHERE current_smk_id = %(current_smk_id)s AND next_smk_id = %(next_smk_id)s
    """
    if shared_conn:
        return shared_conn.selectData(sql, {'current_smk_id': current_smk_id, 'next_smk_id': next_smk_id})
    
    conn = None
    result = {'status': False, 'data': [], 'msg': 'Connection setup failed.'}
    
    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectData(sql, {'current_smk_id': current_smk_id, 'next_smk_id': next_smk_id})
            return result
        return {'status': False, 'msg': 'DB Connection failed'}
    except Exception as e:
        Log.error(f'Exception | get_workflow_rule | Msg: {str(e)}')
        return {'status': False, 'msg': str(e)}
    finally:
        if conn: conn.close()

def get_next_allowed_phases(current_smk_id: int, shared_conn=None) -> dict:
    sql = """
        SELECT next_smk_id, rule_detail
        FROM public.sr_ms_workflow_rules
        WHERE current_smk_id = %(current_smk_id)s
        ORDER BY next_smk_id ASC
    """

    if shared_conn:
        return shared_conn.selectDataHeader(sql, {'current_smk_id': current_smk_id})
    
    conn = None
    result = {'status': False, 'data': [], 'msg': 'Connection setup failed.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectDataHeader(sql, {'current_smk_id': current_smk_id})
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': 'Failed to connect to database.'}
    except Exception as e:
        Log.error(f'DB Exception | get_next_allowed_phases | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()

def get_mandatory_docs(rule_id: int, shared_conn=None) -> dict:
    sql = """
        SELECT attach_ctg
        FROM public.sr_mandatory_docs
        WHERE rule_id = %(rule_id)s
    """
    if shared_conn:
        return shared_conn.selectData(sql, {'rule_id': rule_id})
    
    conn = None
    result = {'status': False, 'data': [], 'msg': 'Connection setup failed.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectData(sql, {'rule_id': rule_id})
            return result
        return {'status': False, 'msg': 'DB Connection failed'}
    except Exception as e:
        Log.error(f'Exception | get_mandatory_docs | Msg: {str(e)}')
        return {'status': False, 'msg': str(e)}
    finally:
        if conn: conn.close()

def get_uploaded_docs(sr_no: str, shared_conn=None) -> dict:
    sql = """
        SELECT DISTINCT attach_ctg
        FROM public.sr_attachment
        WHERE sr_no = %(sr_no)s
    """
    if shared_conn:
        return shared_conn.selectData(sql, {'sr_no': sr_no})
    
    conn = None
    result = {'status': False, 'data': [], 'msg': 'Connection setup failed.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectData(sql, {'sr_no': sr_no})
            return result
        return {'status': False, 'msg': 'DB Connection failed'}
    except Exception as e:
        Log.error(f'Exception | get_uploaded_docs | Msg: {str(e)}')
        return {'status': False, 'msg': str(e)}
    finally:
        if conn: conn.close()

def get_required_role_for_phase(current_smk_id: int, shared_conn=None) -> int:
    """Finds which role owns the current phase."""
    sql = """
        SELECT allowed_picrole 
        FROM public.sr_ms_workflow_rules 
        WHERE current_smk_id = %(current_smk_id)s 
        LIMIT 1;
    """
    if shared_conn:
        return shared_conn.selectData(sql, {'current_smk_id': current_smk_id})
    
    conn = None
    result = {'status': False, 'data': [], 'msg': 'Connection setup failed.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectData(sql, {'current_smk_id': current_smk_id})
            if result.get('status') and result.get('data'):
                return result['data'][0][0]  # Return allowed_picrole
        return None
    except Exception as e:
        Log.error(f'Exception | get_required_role_for_phase | Msg: {str(e)}')
        return None
    finally:
        if conn: conn.close()