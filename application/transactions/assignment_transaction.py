from application.transactions import srlogs_transaction, workflow_transaction
from common.midiconnectserver.midilog import Logger
from common.midiconnectserver import DatabasePG
from ..models import assignment_model
from ..utils.converters import parse_rows, parse_single_row

Log = Logger()


def get_assign_page_data_trx(sr_no: str, nik: str) -> dict:
    """
    Ambil semua data yang dibutuhkan halaman assignment.
    Validasi: user harus IT SM yang ter-assign pada SR ini.

    Return:
    - sr_detail: detail SR
    - picroles: list PIC roles yang bisa di-assign (dari DB)
    - it_users: list user IT yang bisa di-assign
    - current_assignments: assignment yang sudah ada
    - is_locked: True jika assignment sudah di-submit (status != 105)
    """
    try:
        # 1. Validasi: user harus IT SM pada SR ini
        sm_result = assignment_model.get_user_role_assignment_on_sr_model(sr_no, nik, 'IT SM')
        sm_row = parse_single_row(sm_result)
        if not sm_row:
            return {'status': False, 'data': [], 'msg': 'Anda bukan IT SM pada SR ini atau tidak memiliki akses.'}

        # 2. Ambil detail SR
        sr_result = assignment_model.get_sr_detail_with_status_model(sr_no)
        sr_detail = parse_single_row(sr_result)
        if not sr_detail:
            return {'status': False, 'data': [], 'msg': 'SR tidak ditemukan.'}
        
        # 3. Tentukan apakah assignment sudah locked
        is_locked = sr_detail.get('smk_id') != assignment_model.STATUS_BACKLOG_SCRUM

        # 4. Ambil PIC roles yang bisa di-assign (dari DB)
        picroles_result = assignment_model.get_assignable_picroles_model()
        picroles = parse_rows(picroles_result)
        assignable_role_ids = [r['it_role_id'] for r in picroles]

        # 5. Ambil daftar user IT
        users_result = assignment_model.get_it_users_model()
        it_users = parse_rows(users_result)

        # 6. Ambil assignment yang sudah ada (hanya PIC roles dari DB)
        assignments_result = assignment_model.get_sr_assignments_model(sr_no, assignable_role_ids)
        current_assignments = parse_rows(assignments_result)

        #7. Fetch Target Dates for the SM to fill
        target_dates_result = srlogs_transaction.get_target_date_trx(sr_no)
        target_dates = target_dates_result.get('data', [])

        return {
            'status': True,
            'data': {
                'sr_detail': sr_detail,
                'picroles': picroles,
                'it_users': it_users,
                'current_assignments': current_assignments,
                'is_locked': is_locked,
                'target_dates': target_dates
            }
        }
    except Exception as e:
        Log.error(f'Exception | get_assign_page_data_trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}

def submit_assignments_trx(sr_no: str, nik: str, form_data: dict, shared_conn=None) -> dict:
    """
    Submit assignment PIC pada SR (Tanpa advance phase).
    """
    try:
        # 1. Validasi: user harus IT SM pada SR ini
        sm_result = assignment_model.get_user_role_assignment_on_sr_model(sr_no, nik, 'IT SM')
        sm_row = parse_single_row(sm_result)
        if not sm_row:
            return {'status': False, 'data': [], 'msg': 'Anda bukan IT SM pada SR ini.'}

        # 2. Validasi: SR harus masih BACKLOG SCRUM (105)
        sr_result = assignment_model.get_sr_detail_with_status_model(sr_no)
        sr_detail = parse_single_row(sr_result)
        if not sr_detail:
            return {'status': False, 'data': [], 'msg': 'SR tidak ditemukan.'}
        if sr_detail.get('smk_id') != assignment_model.STATUS_BACKLOG_SCRUM:
            return {'status': False, 'data': [], 'msg': 'Assignment sudah dikunci. SR tidak lagi dalam status Backlog Scrum.'}

        # 3. Parse form: assign_user[] dan assign_role[]
        user_list = form_data.getlist('assign_user[]') if hasattr(form_data, 'getlist') else form_data.get('assign_user[]', [])
        role_list = form_data.getlist('assign_role[]') if hasattr(form_data, 'getlist') else form_data.get('assign_role[]', [])

        if isinstance(user_list, str): user_list = [user_list]
        if isinstance(role_list, str): role_list = [role_list]

        assignments = []
        for user_nik, role_id_str in zip(user_list, role_list):
            user_nik = user_nik.strip() if user_nik else ''
            role_id_str = role_id_str.strip() if role_id_str else ''
            if not user_nik or not role_id_str: continue
            assignments.append({'nik': user_nik, 'it_role_id': int(role_id_str)})

        if not assignments:
            return {'status': False, 'data': [], 'msg': 'Tidak ada assignment yang diisi.'}

        # 4. Validasi: minimal 1 user per role
        picroles_result = assignment_model.get_assignable_picroles_model()
        picroles = parse_rows(picroles_result)
        role_map = {r['it_role_id']: r['it_role_detail'] for r in picroles}

        assigned_roles = {a['it_role_id'] for a in assignments}
        for it_role_id, role_name in role_map.items():
            if it_role_id not in assigned_roles:
                return {'status': False, 'data': [], 'msg': f'Minimal 1 user harus di-assign untuk role {role_name}.'}

        # 5. Validasi: NIK harus ada di daftar IT users
        users_result = assignment_model.get_it_users_model()
        it_users = parse_rows(users_result)
        valid_niks = {u['nik'] for u in it_users}
        for a in assignments:
            if a['nik'] not in valid_niks:
                return {'status': False, 'data': [], 'msg': f"NIK {a['nik']} tidak terdaftar sebagai User IT."}

        # 6. Tentukan is_active
        seen_roles = set()
        for a in assignments:
            a['is_active'] = a['it_role_id'] not in seen_roles
            seen_roles.add(a['it_role_id'])

        # 7. Insert assignments (Database Connection Logic)
        local_conn = False
        if shared_conn is None:
            shared_conn = DatabasePG("supabase", autocommit=False)
            local_conn = True

        try:
            insert_result = assignment_model.insert_assignments_model(sr_no, assignments, nik, shared_conn)
            if not insert_result.get('status'):
                raise Exception(insert_result.get('msg', 'Gagal insert assignment'))

            if local_conn:
                shared_conn._conn.commit()

            return {'status': True, 'data': [], 'msg': 'Assignment PIC berhasil disimpan.'}

        except Exception as e:
            if local_conn:
                try: shared_conn._conn.rollback()
                except Exception: pass
            raise e
        finally:
            if local_conn and shared_conn:
                shared_conn.close()

    except Exception as e:
        Log.error(f'Exception | submit_assignments_trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}

def get_gm_assign_page_data_trx(sr_no: str, nik: str) -> dict:
    """
    Ambil data untuk halaman assign IT SM oleh IT GM.
    Validasi: user harus IT GM yang ter-assign pada SR ini.

    Return:
    - sr_detail: detail SR
    - sm_options: list IT SM yang bisa dipilih (nik + nama)
    - current_sm: IT SM yang sudah ter-assign (jika ada)
    - is_locked: True jika status sudah bukan 104
    """
    try:
        # 1. Validasi: user harus IT GM pada SR ini
        gm_result = assignment_model.get_user_role_assignment_on_sr_model(sr_no, nik, 'IT GM')
        gm_row = parse_single_row(gm_result)
        if not gm_row:
            return {'status': False, 'data': [], 'msg': 'Anda bukan IT GM pada SR ini atau tidak memiliki akses.'}

        # 2. Ambil detail SR
        sr_result = assignment_model.get_sr_detail_with_status_model(sr_no)
        sr_detail = parse_single_row(sr_result)
        if not sr_detail:
            return {'status': False, 'data': [], 'msg': 'SR tidak ditemukan.'}

        # 3. Tentukan apakah assignment sudah locked (status bukan 104)
        is_locked = sr_detail.get('smk_id') != assignment_model.STATUS_IT_GM_REVIEW

        # 4. Ambil opsi IT SM dari NIK yang sudah dikonfigurasi
        sm_niks = list(workflow_transaction.IT_SM_NIKS)
        sm_result = assignment_model.get_sm_options_model(sm_niks)
        sm_options = parse_rows(sm_result)

        # 5. Cek apakah IT SM sudah ter-assign
        sm_role_id = assignment_model.get_it_role_id_by_name_model('IT SM')
        assigned_result = assignment_model.get_sr_assignments_model(sr_no, [sm_role_id] if sm_role_id else [])
        current_sm = parse_rows(assigned_result)

        return {
            'status': True,
            'data': {
                'sr_detail': sr_detail,
                'sm_options': sm_options,
                'current_sm': current_sm,
                'is_locked': is_locked,
            }
        }
    except Exception as e:
        Log.error(f'Exception | get_gm_assign_page_data_trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}


def submit_sm_assignment_trx(sr_no: str, nik: str, form_data: dict, shared_conn=None) -> dict:
    """
    IT GM assign IT SM pada SR. (Hanya assignment, tanpa advance status).

    Validasi:
    1. User harus IT GM pada SR ini
    2. SR harus masih status IT GM Review (104)
    3. NIK IT SM yang dipilih harus salah satu dari IT_SM_NIKS yang dikonfigurasi
    """
    try:
        # 1. Validasi: user harus IT GM pada SR ini
        gm_result = assignment_model.get_user_role_assignment_on_sr_model(sr_no, nik, 'IT GM')
        gm_row = parse_single_row(gm_result)
        if not gm_row:
            return {'status': False, 'data': [], 'msg': 'Anda bukan IT GM pada SR ini.'}

        # 2. Validasi: SR harus masih status 104
        sr_result = assignment_model.get_sr_detail_with_status_model(sr_no)
        sr_detail = parse_single_row(sr_result)
        if not sr_detail:
            return {'status': False, 'data': [], 'msg': 'SR tidak ditemukan.'}
        if sr_detail.get('smk_id') != assignment_model.STATUS_IT_GM_REVIEW:
            return {'status': False, 'data': [], 'msg': 'Assignment sudah dikunci. SR tidak lagi dalam status IT GM Review.'}

        # 3. Ambil NIK IT SM yang dipilih dari form
        selected_sm_nik = form_data.get('selected_sm_nik', '').strip()
        if not selected_sm_nik:
            return {'status': False, 'data': [], 'msg': 'Pilih salah satu IT SM terlebih dahulu.'}

        # 4. Validasi: harus salah satu dari NIK yang dikonfigurasi
        if selected_sm_nik not in workflow_transaction.IT_SM_NIKS:
            return {'status': False, 'data': [], 'msg': 'NIK IT SM tidak valid.'}

        # 5. Ambil role ID IT SM dari DB
        sm_role_id = assignment_model.get_it_role_id_by_name_model('IT SM')
        if not sm_role_id:
            return {'status': False, 'data': [], 'msg': 'Gagal mendapatkan role ID IT SM dari database.'}

        # 6. Insert assignment (Menggunakan shared_conn jika ada, jika tidak buka koneksi baru)
        local_conn = False
        if shared_conn is None:
            shared_conn = DatabasePG("supabase", autocommit=False)
            local_conn = True

        try:
            insert_result = assignment_model.insert_assignments_model(
                sr_no=sr_no,
                assignments=[{'nik': selected_sm_nik, 'it_role_id': sm_role_id}],
                assigned_by=nik,
                shared_conn=shared_conn
            )
            
            if not insert_result.get('status'):
                raise Exception(insert_result.get('msg', 'Gagal insert assignment IT SM'))

            # Hanya commit jika koneksi ini dibuat secara lokal di fungsi ini
            if local_conn:
                shared_conn._conn.commit()

            return {'status': True, 'data': [], 'msg': 'IT SM berhasil di-assign.'}

        except Exception as e:
            if local_conn:
                try:
                    shared_conn._conn.rollback()
                except Exception:
                    pass
            raise e

        finally:
            if local_conn and shared_conn:
                shared_conn.close()

    except Exception as e:
        Log.error(f'Exception | submit_sm_assignment_trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}


def handover_pic_trx(sr_no: str, nik: str, target_assign_id: int) -> dict:
    """
    Oper SR ke user lain di role yang sama.
    Validasi: user yang trigger harus is_active=TRUE di role ini pada SR ini.
    Hanya mengubah is_active — smk_id SR tidak berubah.
    """
    try:
        # 1. Ambil info target assignment
        target_result = assignment_model.get_assignment_by_id_model(target_assign_id)
        target = parse_single_row(target_result)
        if not target:
            return {'status': False, 'data': [], 'msg': 'Target assignment tidak ditemukan.'}

        if target['sr_no'] != sr_no:
            return {'status': False, 'data': [], 'msg': 'Target assignment tidak sesuai dengan SR ini.'}

        it_role_id = target['it_role_id']

        # 2. Validasi: user yang trigger harus is_active=TRUE di role ini
        active_result = assignment_model.get_active_pic_on_sr_model(sr_no, nik)
        active_rows = parse_rows(active_result)
        active_role = next((a for a in active_rows if a['it_role_id'] == it_role_id), None)
        if not active_role:
            return {'status': False, 'data': [], 'msg': 'Anda tidak sedang aktif mengerjakan role ini pada SR ini.'}

        # 3. Toggle is_active
        toggle_result = assignment_model.toggle_active_pic_model(sr_no, it_role_id, target_assign_id)
        if not toggle_result.get('status'):
            return {'status': False, 'data': [], 'msg': toggle_result.get('msg', 'Gagal mengoper SR.')}

        return {'status': True, 'data': [], 'msg': 'SR berhasil dioper ke PIC lain.'}
    except Exception as e:
        Log.error(f'Exception | handover_pic_trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    
def process_gm_approval_trx(sr_no: str, nik: str, form_data: dict, current_smk_id: int, next_smk_id: int) -> dict:
    """
    Orchestrates the GM approval process: Assings an IT SM and advances the phase.
    Handles the database transaction to ensure atomicity outside of the route layer.
    """
    shared_conn = None
    try:
        shared_conn = DatabasePG("supabase", autocommit=False)

        # 1. Execute the Assignment (Pass the shared_conn)
        assign_result = submit_sm_assignment_trx(
            sr_no=sr_no, 
            nik=nik, 
            form_data=form_data, 
            shared_conn=shared_conn
        )
        
        if not assign_result.get('status'):
            raise Exception(f"Assignment gagal: {assign_result.get('msg')}")

        # 2. Execute the Phase Advancement (Pass the shared_conn)
        advance_result = workflow_transaction.advance_sr_phase(
            sr_no=sr_no,
            current_smk_id=current_smk_id,
            next_smk_id=next_smk_id,
            action_by=nik,
            shared_conn=shared_conn
        )
        
        if not advance_result.get('status'):
            raise Exception(f"Advance phase gagal: {advance_result.get('msg')}")

        # If both succeed, commit the transaction
        shared_conn._conn.commit()
        return {'status': True, 'data': [], 'msg': 'IT SM berhasil di-assign dan phase SR diupdate.'}

    except Exception as e:
        if shared_conn:
            try:
                shared_conn._conn.rollback()
            except Exception:
                pass
        Log.error(f'Exception | process_gm_approval_trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}

    finally:
        if shared_conn:
            shared_conn.close()

def process_sm_approval_trx(sr_no: str, nik: str, form_data: dict, current_smk_id: int, next_smk_id: int) -> dict:
    """
    Orchestrates the SM approval process: Assigns PICs and advances the phase atomically.
    """
    shared_conn = None
    try:
        shared_conn = DatabasePG("supabase", autocommit=False)

        # 1. Execute the PIC Assignments
        assign_result = submit_assignments_trx(sr_no, nik, form_data, shared_conn=shared_conn)
        if not assign_result.get('status'):
            raise Exception(f"Assignment gagal: {assign_result.get('msg')}")
        
        date_result = srlogs_transaction.process_target_dates_trx(sr_no, form_data, shared_conn=shared_conn)
        if not date_result.get('status'):
            raise Exception(date_result.get('msg'))

        # 2. Execute the Phase Advancement
        advance_result = workflow_transaction.advance_sr_phase(
            sr_no=sr_no, current_smk_id=current_smk_id, next_smk_id=next_smk_id, 
            action_by=nik, shared_conn=shared_conn
        )
        if not advance_result.get('status'):
            raise Exception(f"Advance phase gagal: {advance_result.get('msg')}")

        shared_conn._conn.commit()
        return {'status': True, 'msg': 'Tim PIC berhasil di-assign dan phase SR diupdate.'}

    except Exception as e:
        if shared_conn:
            try: shared_conn._conn.rollback()
            except Exception: pass
        Log.error(f'Exception | process_sm_approval_trx | Msg: {str(e)}')
        return {'status': False, 'msg': str(e)}
    finally:
        if shared_conn:
            shared_conn.close()

def get_sr_actors_trx(sr_no: str) -> dict:
    """
    Orchestrates the fetching of SR origins and approvers using a single connection.
    Returns a beautifully structured dictionary for the UI.
    """
    conn = None
    result = {'status': False, 'data': {}, 'msg': ''}

    try:
        # 1. Open a single connection for the transaction
        conn = DatabasePG("supabase")
        if not conn:
            result['msg'] = 'Database connection failed.'
            return result

        # 2. Call the separated model functions
        origins_res = assignment_model.get_sr_origins(sr_no, shared_conn=conn)
        approvers_res = assignment_model.get_sr_approvers(sr_no, shared_conn=conn)

        # 3. Validate origins (mandatory)
        if not origins_res.get('status') or not origins_res.get('data'):
            result['msg'] = 'SR Origins not found.'
            return result

        # Extract rows (adjust indices if your selectDataHeader returns differently)
        origins_data = origins_res['data'][1][0] 
        approvers_data = approvers_res['data'][1] if approvers_res.get('status') and approvers_res.get('data') else []

        # 4. Initialize the structure
        ticket_actors = {
            "origins": {
                "requester": {
                    "nik": origins_data[1], 
                    "name": origins_data[2]
                },
                "maker": {
                    "nik": origins_data[3],
                    "name": origins_data[4]
                }
            },
            "approvers": {}
        }

        # 5. Distribute approvers into their specific buckets
        for row in approvers_data:
            #role_id = row[0]
            role_name = row[1]
            user_info = {"nik": row[2], "name": row[3]}
            
            # If this is the first time we are seeing this role, create an empty list for it
            if role_name not in ticket_actors["approvers"]:
                ticket_actors["approvers"][role_name] = []
            
            # Append the user to their specific role list
            ticket_actors["approvers"][role_name].append(user_info)

        # 6. Return success
        result['status'] = True
        result['data'] = ticket_actors
        result['msg'] = 'Actors fetched and structured successfully.'
        return result

    except Exception as e:
        Log.error(f'Transaction Exception | get_sr_actors_trx | Msg: {str(e)}')
        result['msg'] = 'An error occurred while processing SR actors.'
        return result
    finally:
        # Always close the connection
        if conn:
            conn.close()