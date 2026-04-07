from common.midiconnectserver.midilog import Logger
from ..models import my_work_model, assignment_model, task_model
from ..transactions import assignment_transaction
from ..utils.converters import parse_rows, parse_single_row

Log = Logger()

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
                }
            role_id = row.get('it_role_id')
            if role_id and role_id not in sr_map[sr_no]['role_ids']:
                sr_map[sr_no]['role_ids'].append(role_id)
                sr_map[sr_no]['roles'].append(row.get('it_role_detail', ''))

        items = list(sr_map.values())

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


def get_sr_detail_trx(sr_no: str, nik: str) -> dict:
    """
    Ambil semua data untuk halaman detail SR.
    Validasi: user harus ter-assign pada SR ini.

    Return data:
    - sr_detail: info lengkap SR
    - user_roles: role user pada SR ini (bisa multiple)
    - all_assignments: semua assignment pada SR (grouped by role)
    - is_sm: apakah user adalah IT SM pada SR ini
    - can_assign: apakah user bisa assign PIC (SM + status 105)
    - assignment_data: data untuk form assignment (jika is_sm)
    """
    try:
        # 1. Cek apakah user ter-assign pada SR ini
        user_roles_result = my_work_model.get_user_role_on_sr_model(sr_no, nik)
        user_roles = parse_rows(user_roles_result)
        if not user_roles:
            return {'status': False, 'data': [], 'msg': 'Anda tidak memiliki akses pada SR ini.'}

        # 2. Ambil detail SR
        sr_result = my_work_model.get_sr_detail_full_model(sr_no)
        sr_detail = parse_single_row(sr_result)
        if not sr_detail:
            return {'status': False, 'data': [], 'msg': 'SR tidak ditemukan.'}

        # 3. Ambil semua assignment pada SR
        assignments_result = my_work_model.get_all_sr_assignments_model(sr_no)
        all_assignments_raw = parse_rows(assignments_result)

        # Group assignments by role
        assignments_by_role = {}
        for a in all_assignments_raw:
            role_detail = a.get('it_role_detail', 'Unknown')
            if role_detail not in assignments_by_role:
                assignments_by_role[role_detail] = []
            assignments_by_role[role_detail].append(a)

        # 4. Ambil PIC role IDs dari DB (digunakan di beberapa tempat di bawah)
        picroles_result = assignment_model.get_assignable_picroles_model()
        picroles = parse_rows(picroles_result)
        assignable_role_ids = {r['it_role_id'] for r in picroles}

        # 5. Tentukan role user berdasarkan nama role (bukan hardcoded ID)
        is_sm = any(r['it_role_detail'] == 'IT SM' for r in user_roles)
        is_gm = any(r['it_role_detail'] == 'IT GM' for r in user_roles)

        # 6. Apakah bisa assign? (SM + status masih 105 | GM + status masih 104)
        can_assign = is_sm and sr_detail.get('smk_id') == assignment_model.STATUS_BACKLOG_SCRUM
        can_assign_sm = is_gm and sr_detail.get('smk_id') == assignment_model.STATUS_IT_GM_REVIEW

        # 7. Jika SM, siapkan data assignment (picroles + it_users)
        assignment_data = {}
        if is_sm:
            users_result = assignment_model.get_it_users_model()
            it_users = parse_rows(users_result)

            # Assignment yang sudah ada (hanya PIC roles dari DB)
            pic_assignments = [a for a in all_assignments_raw if a.get('it_role_id') in assignable_role_ids]

            assignment_data = {
                'picroles': picroles,
                'it_users': it_users,
                'current_assignments': pic_assignments,
            }

        # 7b. Jika GM, siapkan data assignment IT SM
        gm_assign_data = {}
        if is_gm:
            gm_page = assignment_transaction.get_gm_assign_page_data_trx(sr_no, nik)
            if gm_page.get('status'):
                gm_assign_data = gm_page['data']

        # 8. Jika PIC, ambil tasks — hanya role yang teritorinya match smk_id SR saat ini
        current_smk_id = sr_detail.get('smk_id')
        territory_map = my_work_model.get_role_territory_model()
        pic_roles = [
            r for r in user_roles
            if r['it_role_id'] in assignable_role_ids
            and current_smk_id in territory_map.get(r['it_role_id'], [])
        ]
        pic_sections = []
        for pr in pic_roles:
            role_id = pr['it_role_id']
            tasks_result = task_model.get_tasks_by_sr_and_role_model(sr_no, role_id)
            tasks = parse_rows(tasks_result)
            pic_sections.append({
                'it_role_id': role_id,
                'it_role_detail': pr['it_role_detail'],
                'assign_id': pr['assign_id'],
                'tasks': tasks,
            })

        return {
            'status': True,
            'data': {
                'sr_detail': sr_detail,
                'user_roles': user_roles,
                'all_assignments': all_assignments_raw,
                'assignments_by_role': assignments_by_role,
                'is_sm': is_sm,
                'is_gm': is_gm,
                'can_assign': can_assign,
                'can_assign_sm': can_assign_sm,
                'assignment_data': assignment_data,
                'gm_assign_data': gm_assign_data,
                'is_pic': len(pic_roles) > 0,
                'pic_sections': pic_sections,
            }
        }
    except Exception as e:
        Log.error(f'Exception | get_sr_detail_trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}

def can_approve_sr_trx(sr_no: str, nik: str) -> dict:
    """
    Cek apakah user ini bisa approve SR ini.
    Syarat:
    - User harus ter-assign pada SR ini sebagai IT SM atau Atasan (Manager)
    - Status SR harus di 102, 103, atau 104 (Review/Approved/Rejected)
    """
    try:
        result = my_work_model.can_approve_sr_model(sr_no, nik)
        rows = parse_rows(result)
        if not rows:
            return {'status': False, 'data': [], 'msg': 'Anda tidak memiliki akses untuk approve SR ini.'}

        can_approve = rows[0].get('can_approve', False)
        if can_approve:
            return {'status': True, 'data': [], 'msg': 'Anda dapat approve SR ini.'}
        else:
            return {'status': False, 'data': [], 'msg': 'Anda tidak memiliki akses untuk approve SR ini.'}
    except Exception as e:
        Log.error(f'Exception | can_approve_sr_trx | Msg: {str(e)}')
        return {'status': False, 'data': [], 'msg': str(e)}