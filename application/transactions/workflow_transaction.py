from common.midiconnectserver.midilog import Logger
from ..models import sr_model, workflow_model, karyawan, assignment_model #ADD THIS LATER (cessa)
from transactions import srlogs_transaction, sr_transaction
from datetime import datetime
from ..utils import converters

Log = Logger()

# CHANGE THIS LATER FOR SECURITY CONCERN
IT_PM_NIK = "0214083545"
IT_GM_NIK = "0201080005"
IT_SM_DW_NIK = "0201080008"
IT_SM_BS_NIK = "0208010095"
IT_SM_OPS_NIK = "0208080011"

def advance_sr_phase(sr_no: str, current_logs_id: int, current_smk_id: int, next_smk_id: int, action_by: str, user_role: int) -> dict:
    try:
        # 1. Get the rule from your newly simplified table
        rule_res = workflow_model.get_workflow_rule(current_smk_id, next_smk_id)
        if not rule_res.get('status') or not rule_res.get('data'):
            return {'status': False, 'msg': 'Invalid workflow transition.'}
        
        rule_id = rule_res['data'][0][0]
        allowed_role = rule_res['data'][0][1] # e.g., 1, 7, 8...

        # ==========================================
        # 2. THE BADGE CHECK (Global Role)
        # ==========================================
        if user_role != allowed_role:
            return {'status': False, 'msg': 'You do not have the required role to approve this phase.'}

        # ==========================================
        # 3. THE IDENTITY CHECK (Contextual Authority)
        # ==========================================
        
        if allowed_role == 9: 
            requester_nik = sr_model.get_sr_requester(sr_no)
            if action_by != requester_nik:
                return {'status': False, 'msg': 'Only the original requester can execute this step.'}

        elif allowed_role == 8: 
            requester_nik = sr_model.get_sr_requester(sr_no)
            required_manager_nik = karyawan.get_karyawan_nik_up(requester_nik)
            if action_by != required_manager_nik:
                return {'status': False, 'msg': 'Only the direct supervisor (nik_up) of the requester can approve this step.'}

        elif allowed_role == 1:
            if action_by != IT_GM_NIK:
                return {'status': False, 'msg': 'Only the IT General Manager can approve this step.'}
                
        elif allowed_role == 2:
            if action_by != IT_PM_NIK:
                return {'status': False, 'msg': 'Only the IT Project Manager can approve this step.'}

        elif allowed_role == 3:
            if action_by not in [IT_SM_DW_NIK, IT_SM_BS_NIK, IT_SM_OPS_NIK]:
                return {'status': False, 'msg': 'Only an IT Senior Manager can approve this step.'}

        elif allowed_role in [4, 5, 6, 7]: # Assuming these are your working roles
            #Check user assigned role here (cessa)
            """
            assigned_role = assignment_model.get_role_for_assigned_user(sr_no, action_by)
            
            if not assigned_role or assigned_role != allowed_role:
                return {'status': False, 'msg': 'You must be specifically assigned to this ticket to execute this phase.'}
            """
        # ==========================================
        # 4. Validate Mandatory Documents 
        # ==========================================
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
        
        # ==========================================
        # 5. Execute the Database Log Updates
        # ==========================================
        if current_logs_id > 1:
            close_result = srlogs_transaction.update_sr_log_trx(current_logs_id)
            if not close_result.get('status'):
                return {'status': False, 'msg': f"Failed to close current log: {close_result.get('msg')}"}

        # 5. Open the new phase log
        new_phase_data = {
            'sr_no': sr_no,
            'smk_id': next_smk_id,
            'action_by': action_by
        }
        create_log_result = srlogs_transaction.create_sr_log_trx(new_phase_data)
        if not create_log_result.get('status'):
             return {'status': False, 'msg': f"Failed to start new log: {create_log_result.get('msg')}"}

        # 6. Update the master SR request table so the system knows where the SR currently is
        sr_prog_result = sr_model.update_sr_prog({'sr_no': sr_no, 'smk_id': next_smk_id})
        if not sr_prog_result.get('status'):
             return {'status': False, 'msg': f"Failed to update main SR status: {sr_prog_result.get('msg')}"}

        return {'status': True, 'msg': 'Phase advanced successfully.'}

    except Exception as e:
        Log.error(f"Exception | Advance Phase Trx | Msg: {str(e)}")
        return {'status': False, 'msg': str(e)}
    
def validate_sr_action_eligibility(sr_no: str, user_nik: str, max_allowed_smk_id: int = 1) -> dict:
    """
    Fetches the SR data and checks if a user can dynamically modify an SR.
    """
    try:
        # ==========================================
        # 1. FETCH THE FULL DATA (Including Attachments!)
        # ==========================================
        # We call your existing transaction so we don't duplicate code
        fetch_result = sr_transaction.get_edit_sr_trx(sr_no) 
        
        if not fetch_result.get('status') or not fetch_result.get('data'):
            # If the SR isn't found, pass the error straight back to the route
            return fetch_result 
            
        # Extract the dictionary (your get_edit_sr_trx returns it in a list)
        sr_dict = fetch_result['data'][0] 
        
        current_smk_id = sr_dict.get('smk_id')
        requester_nik = sr_dict.get('req_id')

        # ==========================================
        # 2. THE CONTEXTUAL ROLE LOOKUP
        # ==========================================
        user_context_role = None

        if user_nik == requester_nik:
            user_context_role = 9
        else:
            #Check user assigned role here (cessa)
            """
            assigned_role_id = assignment_model.get_role_for_assigned_user(sr_no, user_nik)
            
            if assigned_role_id:
                user_context_role = assigned_role_id
            else:
                if user_nik == IT_PM_NIK:
                    user_context_role = 2 
            """

        if user_context_role is None:
            return {'status': False, 'msg': 'Unauthorized: You have no assigned role for this Service Request.'}

        # ==========================================
        # 3. THE PHASE THRESHOLD CHECK 
        # ==========================================
        if current_smk_id > max_allowed_smk_id:
            if user_context_role != 1: 
                return {
                    'status': False, 
                    'msg': f'SR is locked. It is already in Phase {current_smk_id} and can no longer be modified.'
                }

        # If they survive the Bouncer, hand them the FULL data (attachments included)!
        return {'status': True, 'msg': 'Eligible for action.', 'data': [sr_dict]}

    except Exception as e:
        Log.error(f"Exception | Validate SR Action | Msg: {str(e)}")
        return {'status': False, 'msg': 'An error occurred while verifying permissions.', 'data': []}