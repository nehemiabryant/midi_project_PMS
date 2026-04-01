import traceback, pandas as pd
from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()

def get_next_iteration(sr_no: str, attach_ctg: int, shared_conn=None) -> int:
    sql = """
        SELECT COALESCE(MAX(iteration), 0) + 1 AS next_iter
        FROM public.sr_attachments
        WHERE sr_no = %(sr_no)s AND attach_ctg = %(attach_ctg)s
    """

    if shared_conn:
        result = shared_conn.selectData(sql, {'sr_no': sr_no, 'attach_ctg': attach_ctg})
        if result.get('status') and result.get('data'):
            return result['data'][0][0] 

    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectData(sql, {'sr_no': sr_no, 'attach_ctg': attach_ctg})
            if result.get('status') and result.get('data'):
                return result['data'][0][0] 
            else:
                Log.error(f'DB Error | Msg: {result.get("msg")}')
                return {'status': False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | get_next_iteration | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Gagal Koneksi Database!'}
    finally:
        if conn: conn.close()

def insert_attachment(db_params: dict, shared_conn=None) -> dict:
    sql = """
        INSERT INTO public.sr_attachments (sr_no, attach_ctg, file_url, iteration)
        VALUES (%(sr_no)s, %(attach_ctg)s, %(file_url)s, %(iteration)s)
    """

    if shared_conn:
        result = shared_conn.executeDataNoCommit(sql, db_params) # executeData has autocommit handling
        return result

    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.executeData(sql, db_params) # executeData has autocommit handling
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | insert_attachment | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Gagal Koneksi Database!'}
    finally:
        if conn: conn.close()

def get_latest_attachments(sr_no: str, shared_conn=None) -> dict:
    # A clever query to fetch ONLY the highest iteration for each category!
    sql = """
        SELECT attach_ctg, file_url
        FROM public.sr_attachments a
        WHERE sr_no = %(sr_no)s
          AND iteration = (
              SELECT MAX(iteration)
              FROM public.sr_attachments b
              WHERE b.sr_no = a.sr_no AND b.attach_ctg = a.attach_ctg
          )
    """

    if shared_conn:
        result = shared_conn.selectDataHeader(sql, {'sr_no': sr_no})
        return result

    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectDataHeader(sql, {'sr_no': sr_no})
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | get_latest_attachments | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Gagal Koneksi Database!'}
    finally:
        if conn: conn.close()

def get_view_only_attachments(sr_no: str, shared_conn=None) -> dict:
    """
    Fetches the highest iteration for each category, 
    joined with the category name for the frontend UI.
    """
    sql = """
        SELECT a.attach_ctg, c.attach_details, a.file_url
        FROM public.sr_attachments a
        JOIN public.sr_ms_attach_category c ON a.attach_ctg = c.attach_ctg
        WHERE a.sr_no = %(sr_no)s
          AND a.iteration = (
              SELECT MAX(iteration)
              FROM public.sr_attachments b
              WHERE b.sr_no = a.sr_no AND b.attach_ctg = a.attach_ctg
          )
        ORDER BY a.attach_ctg ASC;
    """
    
    if shared_conn:
        return shared_conn.selectDataHeader(sql, {'sr_no': sr_no})
    
    conn = None
    result = {'status': False, 'data': [], 'msg': 'Invalid parameters.'}

    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectDataHeader(sql, {'sr_no': sr_no})
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | get_view_only_attachments | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Gagal Koneksi Database!'}
    finally:
        if conn: conn.close()

def get_required_docs_for_phase(current_smk_id: int, shared_conn=None) -> dict:
    """
    Finds all document categories that might be required by the outgoing rules of the current phase.
    Uses DISTINCT so if multiple rules require the same document, it only shows up once.
    """
    sql = """
        SELECT DISTINCT c.attach_ctg, c.attach_details
        FROM public.sr_mandatory_docs m
        JOIN public.sr_ms_workflow_rules r ON m.rule_id = r.rule_id
        JOIN public.sr_ms_attach_category c ON m.attach_ctg = c.attach_ctg
        WHERE r.current_smk_id = %(current_smk_id)s
        ORDER BY c.attach_ctg ASC;
    """
    
    if shared_conn:
        return shared_conn.selectDataHeader(sql, {'current_smk_id': current_smk_id})
        
    try:
        conn = DatabasePG("supabase")
        if conn:
            result = conn.selectDataHeader(sql, {'current_smk_id': current_smk_id})
            return result
        else:
            Log.error(f'DB Error | Msg: {result.get("msg")}')
            return {'status': False, 'data': [], 'msg': result.get('msg')}
    except Exception as e:
        Log.error(f'DB Exception | get_required_docs_for_phase | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': 'Gagal Koneksi Database!'}
    finally:
        if conn: conn.close()