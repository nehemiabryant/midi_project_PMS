from common.midiconnectserver.midilog import Logger
from common.midiconnectserver import DatabasePG
from ..models import sr_model, workflow_model, karyawan, assignment_model
from ..transactions import srlogs_transaction, sr_transaction
from ..utils import converters

Log = Logger()

# CHANGE THIS LATER FOR SECURITY CONCERN
# TODO: Ganti dengan query DB ketika tabel sr_user mendukung designasi role SM/PM/GM
IT_PM_NIK = "0214083545"
IT_GM_NIK = "0201080005"
IT_SM_NIKS = {"0201080008", "0208010095", "0208080011"}  # DW, BS, OPS

# Auto-assign: ketika SR masuk ke status ini, langsung assign ke NIK yang sudah ditentukan
AUTO_ASSIGN_ON_PHASE = {
    103: {'nik': IT_PM_NIK, 'it_role_id': 2},  # 102→103: assign IT PM
    104: {'nik': IT_GM_NIK, 'it_role_id': 1},  # 103→104: assign IT GM
}

def advance_sr_phase(sr_no: str, current_smk_id: int, next_smk_id: int, action_by: str, shared_conn=None, is_adjustment=False) -> dict:
    try:
        if not is_adjustment:
            rule_res = workflow_model.get_workflow_rule(current_smk_id, next_smk_id)
            if not rule_res.get('status') or not rule_res.get('data'):
                Log.warning(f'advance_sr_phase | SR: {sr_no} | NIK: {action_by} | Invalid transition {current_smk_id}→{next_smk_id}')
                return {'status': False, 'msg': 'Invalid workflow transition.'}

            rule_id = rule_res['data'][0][0]
            allowed_role = rule_res['data'][0][1]
        else:
            rule_id = None

        # ==========================================
        # 2. THE BADGE CHECK (Global Role)
        # ==========================================
        if not is_adjustment:

            # ==========================================
            # 3. THE IDENTITY CHECK (Contextual Authority)
            # ==========================================

            if allowed_role == 9:
                requester_nik = sr_model.get_sr_requester(sr_no)
                if action_by != requester_nik:
                    Log.warning(f'advance_sr_phase | SR: {sr_no} | NIK: {action_by} | Bukan requester (expected: {requester_nik})')
                    return {'status': False, 'msg': 'Only the original requester can execute this step.'}

            elif allowed_role == 8:
                requester_nik = sr_model.get_sr_requester(sr_no)
                required_manager_nik = karyawan.get_karyawan_nik_up(requester_nik)
                if action_by != required_manager_nik:
                    Log.warning(f'advance_sr_phase | SR: {sr_no} | NIK: {action_by} | Bukan manager requester (expected: {required_manager_nik})')
                    return {'status': False, 'msg': 'Only the direct supervisor (nik_up) of the requester can approve this step.'}

            elif allowed_role == 1:
                if action_by != IT_GM_NIK:
                    Log.warning(f'advance_sr_phase | SR: {sr_no} | NIK: {action_by} | Bukan IT GM')
                    return {'status': False, 'msg': 'Only the IT General Manager can approve this step.'}

            elif allowed_role == 2:
                if action_by != IT_PM_NIK:
                    Log.warning(f'advance_sr_phase | SR: {sr_no} | NIK: {action_by} | Bukan IT PM')
                    return {'status': False, 'msg': 'Only the IT Project Manager can approve this step.'}

            elif allowed_role == 3:
                if action_by not in IT_SM_NIKS:
                    Log.warning(f'advance_sr_phase | SR: {sr_no} | NIK: {action_by} | Bukan IT SM')
                    return {'status': False, 'msg': 'Only an IT Senior Manager can approve this step.'}

            elif allowed_role in [4, 5, 6, 7]:
                is_assigned = assignment_model.check_role_assignment_model(sr_no, action_by, allowed_role)
                if not is_assigned:
                    Log.warning(f'advance_sr_phase | SR: {sr_no} | NIK: {action_by} | Tidak ter-assign dengan role {allowed_role}')
                    return {'status': False, 'msg': 'You must be specifically assigned to this ticket to execute this phase.'}

            # ==========================================
            # 4. Validate Mandatory Documents
            # ==========================================
            docs_res = workflow_model.get_mandatory_docs(rule_id)

            if docs_res.get('status') and docs_res.get('data'):
                mandatory_docs = [row[0] for row in docs_res['data']]

                uploaded_res = workflow_model.get_uploaded_docs(sr_no)
                uploaded_docs = [row[0] for row in uploaded_res.get('data', [])] if uploaded_res.get('status') else []

                missing_docs = [doc for doc in mandatory_docs if doc not in uploaded_docs]

                if missing_docs:
                    Log.warning(f'advance_sr_phase | SR: {sr_no} | NIK: {action_by} | Dokumen wajib belum lengkap: {missing_docs}')
                    return {'status': False, 'msg': f'Cannot advance phase. Missing required document categories: {missing_docs}'}

        # ==========================================
        # 5. Execute the Database Log Updates
        # ==========================================

        # Jika shared_conn diberikan dari luar, pakai itu (tidak commit/rollback sendiri)
        owns_conn = shared_conn is None
        if owns_conn:
            shared_conn = DatabasePG("supabase", autocommit=False)

        try:

            latest_log = srlogs_transaction.get_active_log_id_trx(sr_no, shared_conn)
            db_logs_id = 0
            db_log_smk_id = 0

            if latest_log.get('status') and latest_log.get('data'):
                log_dict = latest_log['data'][0] # Grab the first (and only) dictionary in the list

                db_logs_id = log_dict.get('logs_id', 0)
                db_log_smk_id = log_dict.get('smk_id', 0)

            # B. THE DRIFT DETECTOR
            # If the main table (current_smk_id) doesn't match the latest log,
            # someone manually edited the database! We must heal it.
            if db_logs_id > 0 and db_log_smk_id != current_smk_id:

                # Heal Step 1: Force close the hanging log from the manual edit
                # (We pass a special flag or system ID so auditors know the system did this)
                drift_close_res = srlogs_transaction.update_sr_log_trx(
                    logs_id=db_logs_id,
                    shared_conn=shared_conn
                )

                if not drift_close_res.get('status'):
                    return {'status': False, 'msg': 'Failed to heal database drift.'}

                # Heal Step 2: Since we just closed the old log, we tell the engine
                # there is no active log left to close in the normal flow.
                db_logs_id = 0

                Log.info(f"SYSTEM NOTICE: Healed database drift on SR {sr_no}. Closed dangling log {db_log_smk_id}.")

            # C. THE NORMAL FLOW
            # Now the timeline is completely clean and safe to proceed!

            # Step 5a: Close the current valid log (if it exists)
            if db_logs_id > 0:
                close_result = srlogs_transaction.update_sr_log_trx(db_logs_id, shared_conn)
                if not close_result.get('status'):
                    return {'status': False, 'msg': f"Failed to close current log: {close_result.get('msg')}"}

            # 5. Open the new phase log
            new_phase_data = {
                'sr_no': sr_no,
                'smk_id': next_smk_id,
                'action_by': action_by
            }
            create_log_result = srlogs_transaction.create_sr_log_trx(new_phase_data, shared_conn)
            if not create_log_result.get('status'):
                return {'status': False, 'msg': f"Failed to start new log: {create_log_result.get('msg')}"}

            # 6. Update the master SR request table so the system knows where the SR currently is
            sr_prog_result = sr_model.update_sr_prog({'sr_no': sr_no, 'smk_id': next_smk_id}, shared_conn)
            if not sr_prog_result.get('status'):
                return {'status': False, 'msg': f"Failed to update main SR status: {sr_prog_result.get('msg')}"}

            # 7. Auto-assign jika transisi ini memerlukan assignment otomatis
            if next_smk_id in AUTO_ASSIGN_ON_PHASE:
                target = AUTO_ASSIGN_ON_PHASE[next_smk_id]
                assign_result = assignment_model.insert_assignments_model(
                    sr_no=sr_no,
                    assignments=[{'nik': target['nik'], 'it_role_id': target['it_role_id']}],
                    assigned_by=action_by,
                    shared_conn=shared_conn
                )
                if not assign_result.get('status'):
                    return {'status': False, 'msg': f"Failed to auto-assign: {assign_result.get('msg')}"}

            # 7b. Khusus 101→102: auto-assign nik_up requester sebagai Manager (role 8)
            if next_smk_id == 102:
                requester_nik = sr_model.get_sr_requester(sr_no, shared_conn)
                if not requester_nik:
                    return {'status': False, 'msg': 'Gagal mendapatkan data requester untuk auto-assign manager.'}

                manager_nik = karyawan.get_karyawan_nik_up(requester_nik)
                if not manager_nik:
                    return {'status': False, 'msg': 'Requester tidak memiliki atasan terdaftar (nik_up kosong).'}

                assign_result = assignment_model.insert_assignments_model(
                    sr_no=sr_no,
                    assignments=[{'nik': manager_nik, 'it_role_id': 8}],
                    assigned_by=action_by,
                    shared_conn=shared_conn
                )
                if not assign_result.get('status'):
                    return {'status': False, 'msg': f"Gagal auto-assign manager: {assign_result.get('msg')}"}

            # Hanya commit/close jika kita yang buat koneksi sendiri
            if owns_conn:
                shared_conn._conn.commit()
            return {'status': True, 'msg': 'Phase advanced successfully.'}

        except Exception as e:
            if owns_conn:
                shared_conn._conn.rollback()
            Log.error(f"DB Exception during phase advancement | Msg: {str(e)}")
            return {'status': False, 'msg': 'An error occurred while advancing the phase. No changes were made.'}

        finally:
            if owns_conn:
                shared_conn.close()

    except Exception as e:
        Log.error(f"Exception | Advance Phase Trx | Msg: {str(e)}")
        return {'status': False, 'msg': str(e)}
    
def authorize_sr_access(sr_no: str, user_nik: str, intent: str, max_allowed_smk_id: int=104) -> dict:
    """
    Get the SR data and checks if a user can dynamically modify an SR.
    """
    try:
        # ==========================================
        # 1. FETCH DATA BASED ON INTENT
        # ==========================================
        if intent in ['VIEW', 'APPROVE', 'REASSIGN', 'ADJUSTMENT']:
            # Fetch the lightweight detail view
            # Note: adjust the prefix (e.g., sr_transaction.) if this function is in another module
            sr_dict = sr_transaction.get_sr_detail_trx(sr_no)
            
            if not sr_dict:
                return {'status': False, 'msg': 'SR data not found or an error occurred.', 'data': []}
                
        elif intent == 'EDIT':
            # Fetch THE FULL DATA (Including Attachments!)
            get_edit_result = sr_transaction.get_edit_sr_trx(sr_no) 
            
            if not get_edit_result.get('status') or not get_edit_result.get('data'):
                # If the SR isn't found or errors out, pass it straight back
                return get_edit_result 
                
            sr_dict = get_edit_result['data'][0] 
            
        else:
            return {'status': False, 'msg': 'System Error: Unknown intent.'}

        # Extract context variables from the fetched dictionary
        current_smk_id = sr_dict.get('smk_id')
        requester_nik = sr_dict.get('req_id')

        # ==========================================
        # 2. THE CONTEXTUAL ROLE LOOKUP
        # ==========================================
        user_it_role = None

        if user_nik == requester_nik:
            user_it_role = 9
        else:
            assigned_role = assignment_model.get_it_role_on_sr_model(sr_no, user_nik)
            
            if assigned_role:
                user_it_role = assigned_role
            else:
                if user_nik == IT_PM_NIK:
                    user_it_role = 2 

        if user_it_role is None:
            return {'status': False, 'msg': 'Unauthorized: You have no assigned role for this Service Request.'}

        sr_dict['user_it_role'] = user_it_role
        
        # ==========================================
        # 3. THE PHASE THRESHOLD CHECK 
        # ==========================================
        if user_it_role == 2 and intent in ['ADJUSTMENT', 'REASSIGN']:
            return {'status': True, 'msg': f'PM Admin access granted for {intent}.', 'data': [sr_dict]}

        if intent == 'ADJUSTMENT':
            return {
                'status': False, 
                'msg': 'Access Denied: Only the IT Project Manager can access the Adjustment menu.'
            }
        
        if intent == 'VIEW':
            # If they just want to read it, and they survived the role check above, let them in!
            pass

        elif intent == 'EDIT':
            if user_it_role != 9:
                return {
                    'status': False,
                    'msg': 'Access Denied: Only the original requester can edit the Service Request details.'
                }

            if current_smk_id > max_allowed_smk_id:
                return {
                    'status': False, 
                    'msg': f'SR is locked. It is already in Phase {current_smk_id} and can no longer be modified.'
                }
            
        elif intent == 'APPROVE':
            # If they are trying to load an Approval page, it MUST be their turn!
            required_role = workflow_model.get_required_role_for_phase(current_smk_id)

            if not required_role:
                return {'status': False, 'msg': 'This ticket is closed or in an unknown state.'}

            if user_it_role != required_role:
                return {
                    'status': False,
                    'msg': 'Access Denied: This ticket has already been processed or is waiting on another department.'
                }

        elif intent == 'REASSIGN':
            return {
                'status': False,
                'msg': 'Hanya IT PMO yang dapat melakukan reassignment pada SR ini.'
            }

        # If they survive the Bouncer, hand them the data!
        return {'status': True, 'msg': 'Access granted.', 'data': [sr_dict]}

    except Exception as e:
        Log.error(f"Exception | Validate SR Action | Msg: {str(e)}")
        return {'status': False, 'msg': 'An error occurred while verifying permissions.', 'data': []}
    
def _get_handover_options(sr_no: str, nik: str, current_smk_id: int = None) -> list:
    """
    Bangun opsi handover untuk dropdown jika user is_active=TRUE dan ada kandidat.
    current_smk_id digunakan untuk filter role yang relevan dengan phase saat ini.
    Return list opsi handover atau [] jika tidak ada kandidat.
    Private — hanya dipanggil dari get_dropdown_options.
    """
    try:
        active_result = assignment_model.get_active_pic_on_sr_model(sr_no, nik, current_smk_id)
        if not active_result.get('status') or not active_result.get('data'):
            return []

        headers = active_result['data'][0]
        rows = active_result['data'][1]
        active_rows = converters.convert_to_dicts(rows, headers)

        # Ambil semua kandidat sekaligus (1 query batch) lalu group by role di Python
        active_role_ids = [a['it_role_id'] for a in active_rows]
        role_detail_map = {a['it_role_id']: a['it_role_detail'] for a in active_rows}

        candidates_result = assignment_model.get_all_handover_candidates_model(sr_no, active_role_ids, nik)
        if not candidates_result.get('status') or not candidates_result.get('data'):
            return []

        c_headers = candidates_result['data'][0]
        c_rows = candidates_result['data'][1]
        all_candidates = converters.convert_to_dicts(c_rows, c_headers)

        handover_opts = []
        for c in all_candidates:
            role_detail = role_detail_map.get(c['it_role_id'], '')
            handover_opts.append({
                'action_type': 'handover',
                'next_smk_id': None,
                'rule_detail': f"Oper ke {c['nama']} ({role_detail})",
                'target_assign_id': c['assign_id']
            })

        return handover_opts
    except Exception as e:
        Log.error(f"Exception | _get_handover_options | Msg: {str(e)}")
        return []


def get_dropdown_options(current_smk_id: int, sr_no: str = None, nik: str = None) -> list:
    """
    Ambil opsi dropdown untuk transisi status SR.
    Jika sr_no dan nik diberikan, inject opsi handover jika user is_active dan ada kandidat.
    Backwards compatible — caller lama yang tidak kirim sr_no/nik tidak terpengaruh.
    """
    try:
        db_result = workflow_model.get_next_allowed_phases(current_smk_id)
        options = []

        if db_result.get('status') and db_result.get('data') and len(db_result['data']) >= 2:
            headers = db_result['data'][0]
            rows = db_result['data'][1]
            for opt in converters.convert_to_dicts(rows, headers):
                opt['action_type'] = 'advance'
                options.append(opt)

        if sr_no and nik:
            handover_opts = _get_handover_options(sr_no, nik, current_smk_id)
            options.extend(handover_opts)

        return options
    except Exception as e:
        Log.error(f"Exception | Get Dropdown Options | Msg: {str(e)}")
        return []
    
def get_adjustment_dropdown_options() -> list:
    """
    Ambil semua opsi dropdown (smk_id) untuk PM Adjustment.
    Tidak ada validasi rule, PM bisa melompat ke phase manapun.
    """
    try:
        db_result = workflow_model.get_all_phases_model()
        options = []

        if db_result.get('status') and db_result.get('data') and len(db_result['data']) >= 2:
            headers = db_result['data'][0]
            rows = db_result['data'][1]
            
            for opt in converters.convert_to_dicts(rows, headers):
                # Map standard columns to the names expected by the UI template
                options.append({
                    'next_smk_id': opt.get('smk_id'),
                    'rule_detail': opt.get('smk_ket'),
                    'action_type': 'adjust' # Custom tag in case UI needs to know it's forced
                })

        return options
    except Exception as e:
        Log.error(f"Exception | Get Adjustment Dropdown Options | Msg: {str(e)}")
        return []
    
def get_update_action() -> list:
    """
    Mengembalikan aksi default untuk menyimpan draft / update data 
    tanpa merubah status/phase SR.
    """
    return [{
        'next_smk_id': 'update_only',
        'rule_detail': 'Simpan sebagai Draft (Update Data)',
        'action_type': 'update'
    }]