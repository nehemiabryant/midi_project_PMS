from common.midiconnectserver.midilog import Logger
from ..models import my_work_model, assignment_model, task_model
from ..utils.converters import parse_rows, parse_single_row

Log = Logger()

UAT_PHASES = {112, 113}

# Status class mapping untuk badge styling di template
# TODO: Tambahkan kolom status_class ke sr_ms_ket agar mapping ini bisa di-derive dari DB
STATUS_CLASS_MAP = {
    101: 'status-new',
    102: 'status-review',
    103: 'status-approved',
    104: 'status-rejected',
    105: 'status-backlog',
    106: 'status-progress',
    107: 'status-done',
    108: 'status-backlog',
    109: 'status-progress',
    110: 'status-backlog',
    111: 'status-progress',
    112: 'status-done',
    113: 'status-rejected',
    114: 'status-backlog',
    115: 'status-progress',
    116: 'status-rollout',
    117: 'status-done',
    118: 'status-hold',
    119: 'status-cancelled',
    120: 'status-takeout',
}


def get_my_work_trx(nik: str, search_query: str = '') -> dict:
    """
    Ambil semua SR yang di-assign ke user, group by sr_no.
    Return list item dengan format seragam untuk template my_work.html.
    """
    try:
        result = my_work_model.get_my_work_items_model(nik)
        rows = parse_rows(result)

        territory_map = my_work_model.get_role_territory_model()
        picroles_result = assignment_model.get_assignable_picroles_model()
        assignable_role_ids = {r['it_role_id'] for r in parse_rows(picroles_result)}

        # Group by sr_no — kumpulkan roles per SR
        sr_map = {}
        for row in rows:
            sr_no = row['sr_no']
            if sr_no not in sr_map:
                sr_map[sr_no] = {
                    'sr_no': sr_no,
                    'title': row.get('name', ''),
                    'module': row.get('module', ''),
                    'division': row.get('division', ''),
                    'smk_id': row.get('smk_id'),
                    'status_label': row.get('smk_ket', ''),
                    'status_class': STATUS_CLASS_MAP.get(row.get('smk_id'), 'status-default'),
                    'created_at': row.get('created_at', ''),
                    'roles': [],
                    'role_ids': [],
                    'is_pic': False,
                }
            role_id = row.get('it_role_id')
            if role_id and role_id not in sr_map[sr_no]['role_ids']:
                sr_map[sr_no]['role_ids'].append(role_id)
                sr_map[sr_no]['roles'].append(row.get('it_role_detail', ''))

        items = list(sr_map.values())

        for item in items:
            current_smk_id = item['smk_id']
            
            # Check A: Is user acting as IT PMO during UAT phases?
            is_pm = ('IT PMO' in item['roles']) and (current_smk_id in UAT_PHASES)
            
            # Check B: Does user have a standard active PIC role for this specific phase?
            has_active_pic_role = any(
                role_id in assignable_role_ids and current_smk_id in territory_map.get(role_id, [])
                for role_id in item['role_ids']
            )
            
            # Attach the final boolean
            item['is_pic'] = has_active_pic_role or is_pm

        # Filter berdasarkan search query
        if search_query:
            q = search_query.lower()
            items = [
                item for item in items
                if q in item['sr_no'].lower() or q in item['title'].lower()
            ]

        return {
            'status': True,
            'data': items,
            'total': len(list(sr_map.values()))
        }
    except Exception as e:
        Log.error(f'Exception | get_my_work_trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'total': 0, 'msg': str(e)}


def resolve_sr_access_trx(sr_no: str, nik: str) -> dict:
    """
    Tentukan apa yang bisa dilakukan user pada SR ini di fase saat ini.
    Satu-satunya sumber kebenaran untuk penentuan akses — dipakai oleh
    dispatcher, get_my_work_detail_trx, dan get_manage_detail_trx.

    Return data:
    - is_pic     : punya PIC assignment aktif di fase ini (termasuk IT PMO di UAT)
    - is_sm      : ter-assign sebagai IT SM pada SR ini
    - is_gm      : ter-assign sebagai IT GM pada SR ini
    - is_pm      : IT PMO di fase UAT
    - pic_roles  : list role PIC aktif milik user di fase ini
    - it_pmo_role: row IT PMO jika ada
    - user_roles : semua role user pada SR ini
    - sr_detail  : detail SR
    """
    try:
        user_roles_result = my_work_model.get_user_role_on_sr_model(sr_no, nik)
        user_roles = parse_rows(user_roles_result)
        if not user_roles:
            return {'status': False, 'data': {}, 'msg': 'Anda tidak memiliki akses pada SR ini.'}

        sr_result = my_work_model.get_sr_detail_full_model(sr_no)
        sr_detail = parse_single_row(sr_result)
        if not sr_detail:
            return {'status': False, 'data': {}, 'msg': 'SR tidak ditemukan.'}

        current_smk_id = sr_detail.get('smk_id')
        territory_map = my_work_model.get_role_territory_model()

        picroles_result = assignment_model.get_assignable_picroles_model()
        assignable_role_ids = {r['it_role_id'] for r in parse_rows(picroles_result)}

        is_sm = any(r['it_role_detail'] == 'IT SM' for r in user_roles)
        is_gm = any(r['it_role_detail'] == 'IT GM' for r in user_roles)

        pic_roles = [
            r for r in user_roles
            if r['it_role_id'] in assignable_role_ids
            and current_smk_id in territory_map.get(r['it_role_id'], [])
        ]

        it_pmo_role = next((r for r in user_roles if r['it_role_detail'] == 'IT PMO'), None)
        is_pm = it_pmo_role is not None and current_smk_id in UAT_PHASES

        return {
            'status': True,
            'data': {
                'is_pic': len(pic_roles) > 0 or is_pm,
                'is_sm': is_sm,
                'is_gm': is_gm,
                'is_pm': is_pm,
                'pic_roles': pic_roles,
                'it_pmo_role': it_pmo_role,
                'user_roles': user_roles,
                'sr_detail': sr_detail,
            }
        }
    except Exception as e:
        Log.error(f'Exception | resolve_sr_access_trx | Msg: {str(e)}')
        return {'status': False, 'data': {}, 'msg': str(e)}


def get_my_work_detail_trx(sr_no: str, nik: str) -> dict:
    """
    Ambil semua data untuk halaman detail PIC (View & Upload Task).
    Validasi akses via resolve_sr_access_trx.
    """
    try:
        access = resolve_sr_access_trx(sr_no, nik)
        if not access.get('status'):
            return access

        access_data = access['data']
        sr_detail = access_data['sr_detail']
        user_roles = access_data['user_roles']
        pic_roles = access_data['pic_roles']
        it_pmo_role = access_data['it_pmo_role']
        is_pm = access_data['is_pm']

        all_tasks_result = task_model.get_all_tasks_by_sr_model(sr_no)
        all_tasks = parse_rows(all_tasks_result)
        tasks_by_role = {}
        for t in all_tasks:
            rid = t['it_role_id']
            if rid not in tasks_by_role:
                tasks_by_role[rid] = []
            tasks_by_role[rid].append(t)

        pic_sections = []
        for pr in pic_roles:
            role_id = pr['it_role_id']
            pic_sections.append({
                'it_role_id': role_id,
                'it_role_detail': pr['it_role_detail'],
                'assign_id': pr['assign_id'],
                'tasks': tasks_by_role.get(role_id, []),
            })

        if is_pm:
            pic_sections.append({
                'it_role_id': it_pmo_role['it_role_id'],
                'it_role_detail': 'UAT',
                'assign_id': it_pmo_role['assign_id'],
                'tasks': tasks_by_role.get(it_pmo_role['it_role_id'], []),
            })

        return {
            'status': True,
            'data': {
                'sr_detail': sr_detail,
                'user_roles': user_roles,
                'is_sm': access_data['is_sm'],
                'is_gm': access_data['is_gm'],
                'is_pic': access_data['is_pic'],
                'is_pm': is_pm,
                'pic_sections': pic_sections,
            }
        }
    except Exception as e:
        Log.error(f'Exception | get_my_work_detail_trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}


def get_manage_detail_trx(sr_no: str, nik: str) -> dict:
    """
    Ambil data untuk halaman manage (Read-Only) — IT SM, IT GM, dan role lain
    yang tidak sedang aktif sebagai PIC di fase ini.
    Validasi akses via resolve_sr_access_trx.
    Jika user adalah IT PMO, sertakan data untuk form reassignment.
    """
    try:
        access = resolve_sr_access_trx(sr_no, nik)
        if not access.get('status'):
            return access

        access_data = access['data']
        is_pmo = access_data['it_pmo_role'] is not None

        assignments_result = my_work_model.get_all_sr_assignments_model(sr_no)
        all_assignments_raw = parse_rows(assignments_result)
        assignments_by_role = {}
        for a in all_assignments_raw:
            role_detail = a.get('it_role_detail', 'Unknown')
            if role_detail not in assignments_by_role:
                assignments_by_role[role_detail] = []
            assignments_by_role[role_detail].append(a)

        pmo_form_data = {}
        if is_pmo:
            picroles = parse_rows(assignment_model.get_assignable_picroles_model())
            assignable_role_ids = {r['it_role_id'] for r in picroles}
            pmo_form_data = {
                'picroles': picroles,
                'it_users': parse_rows(assignment_model.get_it_users_model()),
                'current_assignments': [
                    a for a in all_assignments_raw
                    if a.get('it_role_id') in assignable_role_ids
                ],
            }

        return {
            'status': True,
            'data': {
                'sr_detail': access_data['sr_detail'],
                'user_roles': access_data['user_roles'],
                'all_assignments': all_assignments_raw,
                'assignments_by_role': assignments_by_role,
                'is_sm': access_data['is_sm'],
                'is_gm': access_data['is_gm'],
                'is_pmo': is_pmo,
                'pmo_form_data': pmo_form_data,
            }
        }
    except Exception as e:
        Log.error(f'Exception | get_manage_detail_trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}
    
def can_approve_sr_trx(sr_no: str, nik: str) -> dict:
    """
    Cek apakah user ini bisa approve SR ini.
    """
    try:
        result = my_work_model.can_approve_sr(sr_no, nik)

        if result:
            return {'status': True, 'data': [], 'msg': 'Anda dapat approve SR ini.'}
        else:
            return {'status': False, 'data': [], 'msg': 'Anda tidak memiliki akses untuk approve SR ini.'}
    except Exception as e:
        Log.error(f'Exception | can_approve_sr_trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}