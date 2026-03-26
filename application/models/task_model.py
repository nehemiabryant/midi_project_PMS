from common.midiconnectserver import DatabasePG
from common.midiconnectserver.midilog import Logger

Log = Logger()


def get_assignment_info_model(nik: str, sr_no: str) -> dict:
    """Cek apakah user ter-assign pada SR tertentu, ambil assign_id dan it_role info."""
    sql = """
        SELECT sa.assign_id, sa.sr_no, sa.assigned_user, sa.it_role_id,
               it.it_role_detail
        FROM sr_assignments sa
        JOIN sr_ms_it it ON sa.it_role_id = it.it_role_id
        WHERE sa.assigned_user = %(nik)s AND sa.sr_no = %(sr_no)s
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'nik': nik, 'sr_no': sr_no})
    except Exception as e:
        Log.error(f'DB Exception | get_assignment_info | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_tasks_by_sr_and_role_model(sr_no: str, it_role_id: int) -> dict:
    """Ambil semua task pada SR tertentu yang dimiliki oleh it_role yang sama."""
    sql = """
        SELECT t.task_id, t.assign_id, t.task_detail, t.target_date, t.actual_date,
               sa.assigned_user, k.nama AS assigned_user_name
        FROM sr_task t
        JOIN sr_assignments sa ON t.assign_id = sa.assign_id
        LEFT JOIN karyawan_all k ON sa.assigned_user = k.nik
        WHERE sa.sr_no = %(sr_no)s AND sa.it_role_id = %(it_role_id)s
        ORDER BY t.task_id
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'sr_no': sr_no, 'it_role_id': it_role_id})
    except Exception as e:
        Log.error(f'DB Exception | get_tasks_by_sr_and_role | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def get_task_by_id_model(task_id: int) -> dict:
    """Ambil single task beserta info assignment-nya untuk validasi."""
    sql = """
        SELECT t.task_id, t.assign_id, t.task_detail, t.target_date, t.actual_date,
               sa.sr_no, sa.assigned_user, sa.it_role_id
        FROM sr_task t
        JOIN sr_assignments sa ON t.assign_id = sa.assign_id
        WHERE t.task_id = %(task_id)s
    """
    conn = None
    try:
        conn = DatabasePG("supabase")
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectDataHeader(sql, {'task_id': task_id})
    except Exception as e:
        Log.error(f'DB Exception | get_task_by_id | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def create_task_model(assign_id: int, task_detail: str, target_date=None, actual_date=None) -> dict:
    """Insert task baru ke sr_task, return task_id."""
    sql_insert = """
        INSERT INTO sr_task (assign_id, task_detail, target_date, actual_date)
        VALUES (%(assign_id)s, %(task_detail)s, %(target_date)s, %(actual_date)s)
        RETURNING task_id
    """
    conn = None
    try:
        conn = DatabasePG("supabase", autocommit=True)
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectData(sql_insert, {
            'assign_id': assign_id,
            'task_detail': task_detail,
            'target_date': target_date,
            'actual_date': actual_date,
        })
    except Exception as e:
        Log.error(f'DB Exception | create_task | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def update_task_model(task_id: int, task_detail: str, target_date=None, actual_date=None) -> dict:
    """Update task yang sudah ada."""
    sql = """
        UPDATE sr_task
        SET task_detail = %(task_detail)s,
            target_date = %(target_date)s,
            actual_date = %(actual_date)s
        WHERE task_id = %(task_id)s
        RETURNING task_id
    """
    conn = None
    try:
        conn = DatabasePG("supabase", autocommit=True)
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.selectData(sql, {
            'task_id': task_id,
            'task_detail': task_detail,
            'target_date': target_date,
            'actual_date': actual_date,
        })
    except Exception as e:
        Log.error(f'DB Exception | update_task | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()


def delete_task_model(task_id: int) -> dict:
    """Hapus task dari sr_task."""
    sql = "DELETE FROM sr_task WHERE task_id = %(task_id)s"
    conn = None
    try:
        conn = DatabasePG("supabase", autocommit=True)
        if not conn.status.get('status'):
            return {'status': False, 'data': [], 'msg': conn.status.get('msg')}
        return conn.executeData(sql, {'task_id': task_id})
    except Exception as e:
        Log.error(f'DB Exception | delete_task | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        if conn: conn.close()
