from common.midiconnectserver.midilog import Logger
from ..models import srlogs_model, sr_model, workflow_model, karyawan
from datetime import datetime
from ..utils import converters

Log = Logger()

# Import your utility function (adjust the folder path to match your app structure)
IT_PM_NIK = "0214083545"
IT_GM_NIK = "0201080005"
IT_SM_DW_NIK = "0201080008"
IT_SM_BS_NIK = "0208010095"
IT_SM_OPS_NIK = "0208080011"

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
        print(f"Exception | Get SR Logs Trx | Msg: {str(e)}")
        return {'status': False, 'data': [], 'msg': str(e)}


def create_sr_log_trx(raw_data: dict) -> dict:
    """
    Starts a new phase. Automatically calculates the correct iteration 
    and sets the start time.
    """
    try:
        sr_no = raw_data.get('sr_no')
        smk_id = int(raw_data.get('smk_id'))
        
        # 1. Automatically calculate the next iteration for this specific phase
        next_iter = srlogs_model.get_next_iteration(sr_no, smk_id)
        
        # 2. Build the exact parameters the model expects
        db_params = {
            'sr_no': sr_no,
            'smk_id': smk_id,
            'action_by': raw_data.get('action_by'), # E.g., the NIK of the user clicking the button
            'iteration': next_iter
        }
        
        return srlogs_model.create_sr_log(db_params)
        
    except Exception as e:
        print(f"Exception | Create SR Log Trx | Msg: {str(e)}")
        return {'status': False, 'msg': str(e)}


def update_sr_log_trx(logs_id: int) -> dict:
    """
    Finishes a phase by capping off the finished_at timestamp.
    """
    try:
        return srlogs_model.update_sr_log(logs_id)
        
    except Exception as e:
        print(f"Exception | Update SR Log Trx | Msg: {str(e)}")
        return {'status': False, 'msg': str(e)}

def advance_sr_phase(sr_no: str, current_logs_id: int, current_smk_id: int, next_smk_id: int, action_by: str, user_role: int) -> dict:
    try:
        # 1. Get the rule
        rule_res = workflow_model.get_workflow_rule(current_smk_id, next_smk_id)
        if not rule_res.get('status') or not rule_res.get('data'):
            return {'status': False, 'msg': 'Invalid workflow transition.'}
        
        rule_id = rule_res['data'][0][0]
        actor_type = rule_res['data'][0][1]      
        allowed_role = rule_res['data'][0][2]    

        # ==========================================
        # 2. THE SMART SECURITY CHECK
        # ==========================================
        if actor_type == 'ROLE':
            if user_role != allowed_role:
                return {'status': False, 'msg': 'You do not have the required IT role for this phase.'}
                
        elif actor_type == 'DIRECT_MANAGER':
            # 1. Find who requested this SR
            requester_nik = sr_model.get_sr_requester(sr_no)
            # 2. Find who their boss is
            required_manager_nik = karyawan.get_karyawan_nik_up(requester_nik)
            
            if action_by != required_manager_nik:
                return {'status': False, 'msg': 'Only the direct supervisor (nik_up) of the requester can approve this step.'}

        # --- The Hardcoded IT Approvers ---
        elif actor_type == 'IT_PM':
            if action_by != IT_PM_NIK:
                return {'status': False, 'msg': 'Only the IT Project Manager can approve this step.'}
                
        elif actor_type == 'IT_GM':
            if action_by != IT_GM_NIK:
                return {'status': False, 'msg': 'Only the IT General Manager can approve this step.'}
                
        elif actor_type == 'IT_SM':
            if action_by != IT_SM_DW_NIK and action_by != IT_SM_BS_NIK and action_by != IT_SM_OPS_NIK:
                return {'status': False, 'msg': 'Only the IT Senior Manager can approve this step.'}

        # 3. Validate Mandatory Documents 
        docs_res = workflow_model.get_mandatory_docs(rule_id)
        
        if docs_res.get('status') and docs_res.get('data'):
            # Convert list of tuples [(1,), (2,)] into a clean flat list of required IDs: [1, 2]
            mandatory_docs = [row[0] for row in docs_res['data']]
            
            # Get what the user has actually uploaded
            uploaded_res = workflow_model.get_uploaded_docs(sr_no)
            uploaded_docs = [row[0] for row in uploaded_res.get('data', [])] if uploaded_res.get('status') else []
            
            # Check if any mandatory docs are missing from the uploaded list
            missing_docs = [doc for doc in mandatory_docs if doc not in uploaded_docs]
            
            if missing_docs:
                return {'status': False, 'msg': f'Cannot advance phase. Missing required document categories: {missing_docs}'}
        
        # 4. Execute the Database Log Updates
        # Close the active phase log
        if current_logs_id > 1:
            close_result = update_sr_log_trx(current_logs_id)
            if not close_result.get('status'):
                return {'status': False, 'msg': f"Failed to close current log: {close_result.get('msg')}"}

        # 5. Open the new phase log
        new_phase_data = {
            'sr_no': sr_no,
            'smk_id': next_smk_id,
            'action_by': action_by
        }
        create_log_result = create_sr_log_trx(new_phase_data)
        if not create_log_result.get('status'):
             return {'status': False, 'msg': f"Failed to start new log: {create_log_result.get('msg')}"}

        # 6. Update the master SR request table so the system knows where the SR currently is
        sr_prog_result = sr_model.update_sr_prog({'sr_no': sr_no, 'smk_id': next_smk_id})
        if not sr_prog_result.get('status'):
             return {'status': False, 'msg': f"Failed to update main SR status: {sr_prog_result.get('msg')}"}

        return {'status': True, 'msg': 'Phase advanced successfully.'}

    except Exception as e:
        print(f"Exception | Advance Phase Trx | Msg: {str(e)}")
        return {'status': False, 'msg': str(e)}