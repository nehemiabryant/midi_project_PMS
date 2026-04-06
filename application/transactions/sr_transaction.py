from common.midiconnectserver.midilog import Logger
from common.midiconnectserver import DatabasePG
from ..models import sr_model, karyawan, assignment_model
from ..utils.converters import parse_rows, parse_single_row, convert_to_dicts
from . import attachment_transaction

Log = Logger()

def get_all_sr_trx() -> dict:
    try:
        db_result = sr_model.get_sr()
        if not db_result.get('status'):
            return db_result
        return {'status': True, 'data': parse_rows(db_result)}
    except Exception as e:
        Log.error(f'Exception | Get All SR Trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}

def get_my_sr_trx(nik: str) -> dict:
    try:
        db_result = sr_model.get_my_sr(nik)
        if not db_result.get('status'):
            return db_result

        items = parse_rows(db_result)

        return {'status': True, 'data': items}
    except Exception as e:
        Log.error(f'Exception | Get My SR Trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}

def create_sr_trx(raw_data: dict, files: dict) -> dict:
    shared_conn = DatabasePG("supabase", autocommit=False)

    try:
        db_params = {
            'ctg_id': raw_data.get('kategori_sr'),
            'smk_id': 101,
            'maker_id': raw_data.get('maker_id'),
            'req_id': raw_data.get('req_id'),
            'division': raw_data.get('division'),
            'name': raw_data.get('nama_aplikasi'),
            'module': raw_data.get('modul'),
            'purpose': raw_data.get('tujuan'),
            'details': raw_data.get('detail_permohonan'),
            'frequency': raw_data.get('frequency'),
            'value': raw_data.get('values'),
            'value_det': raw_data.get('keterangan_values'),
        }

        num_user_str = raw_data.get('number_of_user')
        if num_user_str and num_user_str.isdigit():
            db_params['num_user'] = int(num_user_str)
        else:
            db_params['num_user'] = 0

        data = sr_model.create_sr(db_params, shared_conn)
        if data.get('status'):
            new_sr_no = data['data'][0][0]

            attachment_transaction.upload_and_record_files(new_sr_no, files, db_params['smk_id'], shared_conn)
            assignments = [{'nik': db_params['req_id'], 'it_role_id': 9}]
            assignment_model.insert_assignments_model(new_sr_no, assignments, db_params['maker_id'], shared_conn)

        if shared_conn:
            shared_conn._conn.commit()

        return data
    except Exception as e:
        if shared_conn:
            shared_conn._conn.rollback()
        Log.error(f'Exception | Create SR Trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    finally:
        shared_conn.close()

def get_edit_sr_trx(sr_no: str) -> dict:
    try:
        db_result = sr_model.get_sr_by_no(sr_no)
        sr_dict = parse_single_row(db_result)
        if not sr_dict:
            return {'status': False, 'data': [], 'msg': 'Service Request not found.'}

        req_nik = sr_dict.get('req_id', '')
        maker_nik = sr_dict.get('maker_id', '')
        req_name = ''
        maker_name = ''


        if req_nik:
            req_result = karyawan.get_karyawan_nama_by_nik(req_nik)
            if isinstance(req_result, str):
                req_name = req_result

        if maker_nik:
            maker_result = karyawan.get_karyawan_nama_by_nik(maker_nik)
            if isinstance(maker_result, str):
                maker_name = maker_result

        sr_dict['user_info'] = {
            'maker': {
                'nik': maker_nik,
                'name': maker_name
            },
            'requester': {
                'nik': req_nik,
                'name': req_name
            }
        }

        attachments = attachment_transaction.get_latest_attachments_trx(sr_no)

        sr_dict['attachments'] = attachments

        return {'status': True, 'data': [sr_dict]}
    except Exception as e:
        Log.error(f'Exception | Get Edit SR Trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}

def update_sr_trx(raw_data: dict, files: dict, sr_no: str, current_smk_id: int) -> dict:
    try:
        db_params = {
            'sr_no': sr_no,
            'req_id': raw_data.get('req_id'),
            'division': raw_data.get('division'),
            'ctg_id': raw_data.get('kategori_sr'),
            'name': raw_data.get('nama_aplikasi'),
            'module': raw_data.get('modul'),
            'purpose': raw_data.get('tujuan'),
            'details': raw_data.get('detail_permohonan'),
            'frequency': raw_data.get('frequency'),
            'value': raw_data.get('values'),
            'value_det': raw_data.get('keterangan_values'),
        }

        num_user_str = raw_data.get('number_of_user')
        if num_user_str and num_user_str.isdigit():
            db_params['num_user'] = int(num_user_str)
        else:
            db_params['num_user'] = 0
        
        data = sr_model.update_sr(db_params)
        if data.get('status'):
            attachment_transaction.upload_and_record_files(sr_no, files, current_smk_id)

        #return sr_model.update_sr(db_params)
        return {'status': True, 'data': data}
        
    except Exception as e:
        Log.error(f'Exception | Update SR Trx | Msg: {str(e)}')
        return {'status': False, 'msg': str(e)}
    
def get_full_dashboard_trx() -> dict:
    """
    Fetches both the top cards and the grid data, returning a complete 
    package for the dashboard template.
    """
    try:
        # 1. Fetch Top Cards
        cards_result = sr_model.get_dashboard_top_cards()
        top_cards = {'total_sr': 0, 'active_sr': 0, 'completed_sr': 0, 'overdue_sr': 0}
        
        if cards_result.get('status') and cards_result.get('data'):
            headers = cards_result['data'][0]
            row = cards_result['data'][1][0]
            top_cards = dict(zip(headers, row))

        # 2. Fetch and Shape the Grid
        grid_result = sr_model.get_dashboard_grid()
        dashboard_grid = {}
        
        if grid_result.get('status') and grid_result.get('data'):
            headers = grid_result['data'][0]
            rows = grid_result['data'][1]
            flat_data = convert_to_dicts(rows, headers)
            
            for row in flat_data:
                phase_key = row['phase_name'] 
                
                if phase_key not in dashboard_grid:
                    dashboard_grid[phase_key] = {
                        'phase_name': phase_key,
                        'total_phase_tickets': 0,
                        'divisions': []
                    }
                
                dashboard_grid[phase_key]['divisions'].append({
                    'name': row['division'],
                    'count': row['ticket_count'],
                    'progress': int(row['global_progress']) # The calculated 0-100%
                })
                
                dashboard_grid[phase_key]['total_phase_tickets'] += row['ticket_count']

        # 3. Return the ultimate package
        return {
            'status': True,
            'top_cards': top_cards,
            'grid': dashboard_grid
        }
        
    except Exception as e:
        Log.error(f"Exception | Full Dashboard Trx | Msg: {str(e)}")
        return {'status': False, 'top_cards': {}, 'grid': {}}
    
def get_srs_by_phase_trx(phase_name: str) -> list:
    """
    Transforms the sidebar SQL results into a clean list of dictionaries.
    Returns: [{'sr_no': 'SR-2026-001', 'app_name': '...', 'ticket_progress': 90, ...}]
    """
    try:
        db_result = sr_model.get_srs_by_phase(phase_name)
        
        if not db_result.get('status') or not db_result.get('data'):
            return [] # Safely return an empty list if no tickets match
            
        headers = db_result['data'][0]
        rows = db_result['data'][1]
        
        # Use your standard converter utility
        sr_list = convert_to_dicts(rows, headers)
        
        # Quick cleanup to ensure progress is a clean integer for the HTML width styles
        for sr in sr_list:
            sr['ticket_progress'] = int(sr['ticket_progress']) if sr['ticket_progress'] else 0
            
        return sr_list
        
    except Exception as e:
        Log.error(f"Exception | Get SRs by Phase Trx | Msg: {str(e)}")
        return []
    
def get_sr_detail_trx(sr_no: str) -> dict:
    """
    Transforms the detail SQL result into a single dictionary.
    Returns: {'sr_no': '...', 'app_name': '...', ...} or None if not found.
    """
    try:
        db_result = sr_model.get_sr_detail(sr_no)
        
        if not db_result.get('status') or not db_result.get('data'):
            return None # Safely return None if ticket doesn't exist
            
        headers = db_result['data'][0]
        rows = db_result['data'][1]
        
        if not rows:
            return None
            
        # Convert the single row into a dictionary
        sr_list = convert_to_dicts(rows, headers)
        sr_detail = sr_list[0]
        
        # Clean up the progress integer
        sr_detail['ticket_progress'] = int(sr_detail['ticket_progress']) if sr_detail.get('ticket_progress') else 0
        
        # You can add more data transformations here if needed 
        # (e.g., fetching comments or attachments for this specific sr_no)
            
        return sr_detail
        
    except Exception as e:
        Log.error(f"Exception | Get SR Detail Trx | Msg: {str(e)}")
        return None