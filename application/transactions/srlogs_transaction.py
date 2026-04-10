from common.midiconnectserver.midilog import Logger
from ..models import srlogs_model
from datetime import datetime
from ..utils import converters

Log = Logger()

def get_sr_logs_trx(sr_no: str) -> dict:
    """
    Fetches all logs for an SR and formats them into a clean list of dictionaries
    using the utility function.
    """
    try:
        db_result = srlogs_model.get_sr_logs(sr_no)
        
        if not db_result.get('status') or not db_result.get('data') or len(db_result['data']) < 2:
            return db_result
        
        headers = db_result['data'][0]
        rows = db_result['data'][1]
            
        formatted_data = converters.convert_to_dicts(rows, headers)
            
        return {'status': True, 'data': formatted_data}
        
    except Exception as e:
        Log.error(f"Exception | Get SR Logs Trx | Msg: {str(e)}")
        return {'status': False, 'data': [], 'msg': str(e)}

def get_active_log_id_trx(sr_no: str, shared_conn=None) -> int:
    """
    Fetches the active log ID for a given SR. This is used to know which log entry to update when closing a phase.
    """
    try:
        db_result = srlogs_model.get_active_log_id(sr_no, shared_conn)
        
        if not db_result.get('status') or not db_result.get('data') or len(db_result['data']) < 2:
            return db_result
        
        headers = db_result['data'][0]
        rows = db_result['data'][1]
            
        formatted_data = converters.convert_to_dicts(rows, headers)
            
        return {'status': True, 'data': formatted_data}
        
    except Exception as e:
        Log.error(f"Exception | Get Active Log ID Trx | Msg: {str(e)}")
        return -1  # Return an invalid ID to signify failure

def create_sr_log_trx(raw_data: dict, shared_conn=None) -> dict:
    """
    Starts a new phase. Automatically calculates the correct iteration 
    and sets the start time.
    """
    try:
        sr_no = raw_data.get('sr_no')
        smk_id = int(raw_data.get('smk_id'))
        
        # 1. Automatically calculate the next iteration for this specific phase
        next_iter = srlogs_model.get_next_iteration(sr_no, smk_id, shared_conn)
        
        # 2. Build the exact parameters the model expects
        db_params = {
            'sr_no': sr_no,
            'smk_id': smk_id,
            'action_by': raw_data.get('action_by'), # E.g., the NIK of the user clicking the button
            'iteration': next_iter
        }
        
        return srlogs_model.create_sr_log(db_params, shared_conn)
        
    except Exception as e:
        Log.error(f"Exception | Create SR Log Trx | Msg: {str(e)}")
        return {'status': False, 'msg': str(e)}


def update_sr_log_trx(logs_id: int, shared_conn=None) -> dict:
    """
    Finishes a phase by capping off the finished_at timestamp.
    """
    try:
        return srlogs_model.update_sr_log(logs_id, shared_conn)
        
    except Exception as e:
        Log.error(f"Exception | Update SR Log Trx | Msg: {str(e)}")
        return {'status': False, 'msg': str(e)}

def get_phase_logs_trx(sr_no: str, shared_conn=None) -> dict:
    db_result = srlogs_model.get_phase_logs(sr_no, shared_conn)
    
    if not db_result or not db_result.get('status') or not db_result.get('data'):
        return {'status': False, 'data': []}

    formatted_data = []

    for row in db_result['data']:
        is_dict = isinstance(row, dict)
        smk_id = row['smk_id'] if is_dict else row[0]
        phase_name = row['phase_name'] if is_dict else row[1]
        started_at = row['first_iteration_start'] if is_dict else row[2]
        finished_at = row['last_iteration_finish'] if is_dict else row[3]

        phase_data = {
            'smk_id': smk_id,
            'phase_name': phase_name,
            'started_at': started_at,
            'finished_at': finished_at,
            'is_milestone': False # Default flag for frontend to know it's a phase
        }

        # Status Logic
        if started_at is None:
            phase_data['status_text'] = "Not Started"
            phase_data['status_color'] = "secondary"
        elif finished_at is None:
            phase_data['status_text'] = "In Progress"
            phase_data['status_color'] = "warning"
        else:
            phase_data['status_text'] = "Completed"
            phase_data['status_color'] = "success"

        # --- ROLLOUT (116) CUSTOM LOGIC ---
        # --- ROLLOUT (116) CUSTOM LOGIC ---
        if smk_id == 116:
            phase_data['is_milestone'] = True
            if started_at:
                # If it has started, it is effectively Live/Deployed. 
                # We ignore finished_at entirely for UI purposes.
                phase_data['status_text'] = "Live" 
                phase_data['status_color'] = "success" 
                phase_data['milestone_date'] = started_at
            else:
                phase_data['status_text'] = "Pending Rollout"
                phase_data['status_color'] = "secondary"

        formatted_data.append(phase_data)

    return {'status': True, 'data': formatted_data}