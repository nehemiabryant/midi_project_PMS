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
    
def update_sr_adjustment_trx(raw_data: dict, sr_no: str) -> dict:
    try:
        db_params = {
            'sr_no': sr_no,
            'q_id': raw_data.get('q_id'),
            'ctg_id': raw_data.get('ctg_id'),
            'prj_id': raw_data.get('prj_id')
        }

        if raw_data.get('status_midikriing') == 'true':
            db_params['status_midikriing'] = True
        elif raw_data.get('status_midikriing') == 'false':
            db_params['status_midikriing'] = False

        # Basic validation
        if not db_params['ctg_id']:
            return {'status': False, 'msg': 'Category ID cannot be empty.'}
        
        if not db_params['q_id']:
            return {'status': False, 'msg': 'Target Quarter cannot be empty.'}
        
        if not db_params['prj_id']:
            return {'status': False, 'msg': 'Project Status cannot be empty.'}
        
        result = sr_model.update_sr_adjustment(db_params)
        
        if result.get('status'):
            return {'status': True, 'msg': 'SR successfully adjusted.', 'data': result.get('data')}
        else:
            return {'status': False, 'msg': result.get('msg')}
            
    except Exception as e:
        Log.error(f'Exception | Update SR Adjustment Trx | Msg: {str(e)}')
        return {'status': False, 'msg': str(e)}
    
def update_sr_quarter_trx(sr_no: str, q_id: int, shared_conn=None) -> dict:
    try:
        db_params = {
            'sr_no': sr_no,
            'q_id': q_id
        }

        if not db_params['q_id']:
            return {'status': False, 'msg': 'Target Quarter cannot be empty.'}
        
        result = sr_model.update_sr_quarter(db_params, shared_conn)

        if result.get('status'):
            return {'status': True, 'msg': 'Target Quarter successfully adjusted.', 'data': result.get('data')}
        else:
            return {'status': False, 'msg': result.get('msg')}
    
    except Exception as e:
        Log.error(f'Exception | Update SR Quarter Trx | Msg: {str(e)}')
        return {'status': False, 'msg': str(e)}
    
def update_sr_project_status_trx(sr_no: str, prj_id: int, shared_conn=None) -> dict:
    try:
        db_params = {
            'sr_no': sr_no,
            'prj_id': prj_id
        }

        if not db_params['prj_id']:
            return {'status': False, 'msg': 'Project Status cannot be empty.'}
        
        result = sr_model.update_sr_project_status(db_params, shared_conn)

        if result.get('status'):
            return {'status': True, 'msg': 'Project Status successfully adjusted.', 'data': result.get('data')}
        else:
            return {'status': False, 'msg': result.get('msg')}
    
    except Exception as e:
        Log.error(f'Exception | Update SR Project Status Trx | Msg: {str(e)}')
        return {'status': False, 'msg': str(e)}

def update_sr_midikriing_status_trx(sr_no: str, status_midikriing: str, shared_conn=None) -> dict:
    try:
        db_params = {
            'sr_no': sr_no
        }

        if status_midikriing == 'true':
            db_params['status_midikriing'] = True
        elif status_midikriing == 'false':
            db_params['status_midikriing'] = False

        result = sr_model.update_sr_midikriing_status(db_params, shared_conn)

        if result.get('status'):
            return {'status': True, 'msg': 'Midikriing Status successfully adjusted.', 'data': result.get('data')}
        else:
            return {'status': False, 'msg': result.get('msg')}

    except Exception as e:
        Log.error(f'Exception | Update SR Midikriing Status Trx | Msg: {str(e)}')
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
                
                if row['division']:
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

def get_active_pics_for_sr_trx(sr_no: str, current_smk_id: int) -> list:
    """Ambil active PIC yang relevan dengan fase saat ini. Returns list of dicts."""
    try:
        result = assignment_model.get_all_active_pics_for_sr_model(sr_no, current_smk_id)
        if not result.get('status') or not result.get('data'):
            return []
        headers, rows = result['data'][0], result['data'][1]
        if not rows:
            return []
        return convert_to_dicts(rows, headers)
    except Exception as e:
        Log.error(f"Exception | get_active_pics_for_sr_trx | Msg: {str(e)}")
        return []
    
def get_all_categories_trx() -> list:
    """
    Retrieves and parses SR categories into a list of dictionaries.
    Uses uniform try-except styling and manual data unpacking.
    """
    try:
        db_result = sr_model.get_all_categories()
        categories = []

        # Check if query was successful and data is properly formatted
        if db_result.get('status') and db_result.get('data') and len(db_result['data']) >= 2:
            headers = db_result['data'][0]
            rows = db_result['data'][1]
            
            # Loop through the parsed dictionaries and append to our list
            for ctg in convert_to_dicts(rows, headers):
                categories.append(ctg)

        return categories
    except Exception as e:
        Log.error(f"Exception | Get All Categories Trx | Msg: {str(e)}")
        return []
    
def get_all_quarters_trx() -> list:
    """
    Retrieves and parses SR quarters into a list of dictionaries.
    Uses uniform try-except styling and manual data unpacking.
    """
    try:
        db_result = sr_model.get_all_quarters()
        quarters = []

        # Check if query was successful and data is properly formatted
        if db_result.get('status') and db_result.get('data') and len(db_result['data']) >= 2:
            headers = db_result['data'][0]
            rows = db_result['data'][1]
            
            # Loop through the parsed dictionaries and append to our list
            for q in convert_to_dicts(rows, headers):
                quarters.append(q)

        return quarters
    except Exception as e:
        Log.error(f"Exception | Get All Quarters Trx | Msg: {str(e)}")
        return []

def get_all_years_trx() -> list:
    """
    Retrieves and parses SR years into a list of dictionaries.
    Uses uniform try-except styling and manual data unpacking.
    """
    try:
        db_result = sr_model.get_all_years()
        years = []

        # Check if query was successful and data is properly formatted
        if db_result.get('status') and db_result.get('data') and len(db_result['data']) >= 2:
            headers = db_result['data'][0]
            rows = db_result['data'][1]
            
            # Loop through the parsed dictionaries and append to our list
            for y in convert_to_dicts(rows, headers):
                years.append(y)

        return years
    except Exception as e:
        Log.error(f"Exception | Get All Years Trx | Msg: {str(e)}")
        return []

def get_all_departments_trx() -> list:
    """
    Retrieves and parses departments into a list of dictionaries.
    Uses uniform try-except styling and manual data unpacking.
    """
    try:
        db_result = sr_model.get_all_departments()
        departments = []

        # Check if query was successful and data is properly formatted
        if db_result.get('status') and db_result.get('data') and len(db_result['data']) >= 2:
            headers = db_result['data'][0]
            rows = db_result['data'][1]
            
            # Loop through the parsed dictionaries and append to our list
            for dept in convert_to_dicts(rows, headers):
                departments.append(dept)

        return departments
    except Exception as e:
        Log.error(f"Exception | Get All Departments Trx | Msg: {str(e)}")
        return []
    
def get_all_sm_trx() -> list:
    try:
        db_result = sr_model.get_all_sm_from_departments()
        if db_result.get('status') and db_result.get('data') and len(db_result['data']) >= 2:
            headers = db_result['data'][0]
            rows = db_result['data'][1]
            return [sm for sm in convert_to_dicts(rows, headers)]
        return []
    except Exception as e:
        Log.error(f"Exception | Get All SM Trx | Msg: {str(e)}")
        return []

def get_all_project_status_trx() -> list:
    """
    Retrieves and parses project statuses into a list of dictionaries.
    Uses uniform try-except styling and manual data unpacking.
    """
    try:
        db_result = sr_model.get_all_project_status()
        statuses = []

        # Check if query was successful and data is properly formatted
        if db_result.get('status') and db_result.get('data') and len(db_result['data']) >= 2:
            headers = db_result['data'][0]
            rows = db_result['data'][1]
            
            # Loop through the parsed dictionaries and append to our list
            for status in convert_to_dicts(rows, headers):
                statuses.append(status)

        return statuses
    except Exception as e:
        Log.error(f"Exception | Get All Project Status Trx | Msg: {str(e)}")
        return []
    
def get_filtered_sr_no_trx(
    filter_year: str = None, 
    filter_q_id: int = None, 
    filter_ctg_id: int = None, 
    filter_midikriing: bool = None,
    filter_dept_id: str = None,
    ) -> dict:
    try:
        db_params = {
            'filter_year': filter_year,
            'filter_q_id': filter_q_id,
            'filter_ctg_id': filter_ctg_id,
            'filter_midikriing': filter_midikriing,
            'filter_dept_id': filter_dept_id,
        }

        db_result = sr_model.get_filtered_sr_no(db_params)
        if not db_result.get('status') or not db_result.get('data'):
            return {'sr_nos': [], 'total_count': 0}
        
        headers = db_result['data'][0]
        rows = db_result['data'][1]
        sr_nos = [row[headers.index('sr_no')] for row in rows]

        return {'sr_nos': sr_nos, 'total_count': len(sr_nos)}
    except Exception as e:
        Log.error(f"Exception | Get Filtered SR No Trx | Msg: {str(e)}")
        return {'sr_nos': [], 'total_count': 0}
    
def get_monitoring_counts_trx(sr_list: list) -> dict:
    try:
        if not sr_list:
            return {'total_count': 0, 'count_completed': 0, 'count_progress': 0, 'count_not_started': 0}

        db_result = sr_model.get_monitoring_counts(sr_list)
        if not db_result.get('status') or not db_result.get('data'):
            return {'total_count': 0, 'count_completed': 0, 'count_progress': 0, 'count_not_started': 0}
        
        data = parse_single_row(db_result)
        return {'status': True, 'data': data if data else {'total_count': 0, 'count_completed': 0, 'count_progress': 0, 'count_not_started': 0}}
    except Exception as e:
        Log.error(f"Exception | Get Monitoring Counts Trx | Msg: {str(e)}")
        return {'total_count': 0, 'count_completed': 0, 'count_progress': 0, 'count_not_started': 0}
    
def get_monitoring_status_time_trx(sr_list: list) -> dict:
    if not sr_list:
        return {'status': True, 'data': {'complete': 0, 'on_time': 0, 'over': 0}}
        
    try:
        db_result = sr_model.get_monitoring_status_time(sr_list)
        if not db_result.get('status'): return db_result
        
        data = parse_single_row(db_result)
        return {'status': True, 'data': data if data else {'complete': 0, 'on_time': 0, 'over': 0}}
    except Exception as e:
        Log.error(f'Exception | Get Status Time Trx | Msg: {str(e)}')
        return {'status': False, 'data': None, 'msg': str(e)}

def get_monitoring_status_overview_trx(sr_list: list) -> dict:
    if not sr_list:
        return {'status': True, 'data': {'completed': 0, 'on_progress': 0, 'not_started': 0}}
        
    try:
        db_result = sr_model.get_monitoring_status_overview(sr_list)
        if not db_result.get('status'): return db_result
        
        data = parse_single_row(db_result)
        return {'status': True, 'data': data if data else {'completed': 0, 'on_progress': 0, 'not_started': 0}}
    except Exception as e:
        Log.error(f'Exception | Get Status Overview Trx | Msg: {str(e)}')
        return {'status': False, 'data': None, 'msg': str(e)}

def get_monitoring_overdue_projects_trx(sr_list: list, limit: int = 50, offset: int = 0) -> dict:
    if not sr_list:
        return {'status': True, 'data': [], 'total_count': 0}
        
    try:
        # Pass the whole list so the DB can find ALL overdue items
        db_result = sr_model.get_monitoring_overdue_projects(sr_list)
        if not db_result.get('status'): return db_result
        
        all_items = parse_rows(db_result)
        total_count = len(all_items)
        
        # Apply pagination slicing in Python
        page_items = all_items[offset : offset + limit]
        
        return {'status': True, 'data': page_items, 'total_count': total_count}
    except Exception as e:
        Log.error(f'Exception | Get Overdue Projects Trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'total_count': 0}

def get_monitoring_complete_projects_trx(sr_list: list, limit: int = 50, offset: int = 0) -> dict:
    if not sr_list:
        return {'status': True, 'data': [], 'total_count': 0}
        
    try:
        # Pass the whole list so the DB can find ALL complete items
        db_result = sr_model.get_monitoring_complete_projects(sr_list)
        if not db_result.get('status'): return db_result
        
        all_items = parse_rows(db_result)
        total_count = len(all_items)
        
        # Apply pagination slicing in Python
        page_items = all_items[offset : offset + limit]
        
        return {'status': True, 'data': page_items, 'total_count': total_count}
    except Exception as e:
        Log.error(f'Exception | Get Complete Projects Trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'total_count': 0}
    
def get_monitoring_all_projects_trx(sr_list: list, limit: int = 50, offset: int = 0) -> dict:
    if not sr_list:
        return {'status': True, 'data': [], 'total_count': 0}
        
    try:
        # Ask the database for all the details
        db_result = sr_model.get_monitoring_all_projects(sr_list)
        if not db_result.get('status'): return db_result
        
        # Parse the rows into dictionaries
        all_items = parse_rows(db_result)
        total_count = len(all_items)
        
        # Apply the exact pagination slice
        page_items = all_items[offset : offset + limit]
        
        return {'status': True, 'data': page_items, 'total_count': total_count}
        
    except Exception as e:
        Log.error(f'Exception | Get All Projects Trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'total_count': 0}