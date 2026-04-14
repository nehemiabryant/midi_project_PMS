from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from flask import jsonify
from common.midiconnectserver.midilog import Logger
from application.transactions import sr_transaction, my_work_transaction, assignment_transaction, workflow_transaction, attachment_transaction
import urllib.parse
from ..helpers.decorators import login_required

Log = Logger()

dashboard_bp = Blueprint('owh_dashboard', __name__, url_prefix='/', template_folder='../templates', static_folder='/static')


@dashboard_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard_menu():
    dashboard_data = sr_transaction.get_full_dashboard_trx()
    return render_template('/page/dashboard.html', user=session['user'], role=session['role'], active_menu='dashboard'
                           , top_cards=dashboard_data.get('top_cards', {}), dashboard_grid=dashboard_data.get('grid', {}))

#BEING KEPT AS A REFERENCE IN CASE SOMETHING GOES WRONG
@dashboard_bp.route('/dashboard-design', methods=['GET', 'POST'])
@login_required
def dashboard_design():
    return render_template('/page/dashboard_design.html', user=session['user'], role=session['role'], active_menu='dashboard')

@dashboard_bp.route('/myWork', methods=['GET'])
@login_required
def myWork_menu():
    nik = session['user']['nik']
    search_query = request.args.get('q', '').strip()

    result = my_work_transaction.get_my_work_trx(nik, search_query)

    if not result.get('status'):
        flash(result.get('msg', 'Gagal memuat data My Work.'), 'error')
        my_work_items = []
        my_work_total = 0
    else:
        my_work_items = result.get('data', [])
        my_work_total = result.get('total', 0)

    return render_template(
        '/page/my_work.html',
        user=session['user'],
        role=session['role'],
        active_menu='my_work',
        my_work_items=my_work_items,
        my_work_total=my_work_total,
        search_query=search_query
    )


@dashboard_bp.route('/myWork/detail/<path:sr_no>', methods=['GET'])
@login_required
def sr_detail_menu(sr_no):
    """Dispatcher — redirect ke sub-route yang sesuai berdasarkan akses user di fase SR saat ini."""
    nik = session['user']['nik']
    access = my_work_transaction.resolve_sr_access_trx(sr_no, nik)

    if not access.get('status'):
        flash(access.get('msg', 'Gagal memuat detail SR.'), 'error')
        return redirect(url_for('owh_dashboard.myWork_menu'))

    if access['data']['is_pic']:
        return redirect(url_for('owh_dashboard.sr_detail_pic', sr_no=sr_no))

    return redirect(url_for('owh_dashboard.sr_detail_view', sr_no=sr_no))


@dashboard_bp.route('/myWork/detail/<path:sr_no>/pic', methods=['GET', 'POST'])
@login_required
def sr_detail_pic(sr_no):
    """Halaman detail PIC — upload task & jalankan workflow."""
    nik = session['user']['nik']
    result = my_work_transaction.get_my_work_detail_trx(sr_no, nik)

    if not result.get('status'):
        flash(result.get('msg', 'Gagal memuat detail SR.'), 'error')
        return redirect(url_for('owh_dashboard.myWork_menu'))

    page_data = result['data']
    sr_detail = page_data.get('sr_detail', {})
    current_smk_id = sr_detail.get('smk_id')
    is_pm = page_data.get('is_pm', False)

    docs_res = attachment_transaction.get_required_docs_for_phase_trx(current_smk_id)
    required_docs = docs_res.get('data', [])
    current_files_dict = attachment_transaction.get_latest_attachments_trx(sr_no)

    if request.method == 'POST':
        files = request.files
        form_smk_id = request.form.get('smk_id', current_smk_id)

        if files:
            try:
                attachment_transaction.upload_and_record_files(sr_no, files, form_smk_id)
                flash('File berhasil diunggah.', 'success')
            except Exception as e:
                flash(f'Gagal mengunggah file: {str(e)}', 'error')
        else:
            flash('Tidak ada file yang dipilih.', 'warning')

        return redirect(url_for('owh_dashboard.sr_detail_pic', sr_no=sr_no))

    dropdown_options = workflow_transaction.get_dropdown_options(current_smk_id, sr_no, nik)
    return render_template(
        '/page/detail_pic.html',
        user=session['user'],
        role=session['role'],
        active_menu='my_work',
        sr_detail=page_data['sr_detail'],
        user_roles=page_data['user_roles'],
        pic_sections=page_data['pic_sections'],
        required_docs=required_docs,
        current_files=current_files_dict,
        dropdown_options=dropdown_options,
        is_pm=is_pm
    )



@dashboard_bp.route('/myWork/detail/<path:sr_no>/workflow', methods=['POST'])
@login_required
def pic_workflow_action(sr_no):
    """PIC melanjutkan status SR atau mengoper ke PIC lain di role yang sama."""
    nik = session['user']['nik']
    data = request.get_json(silent=True) or {}
    action_type = data.get('action_type', 'advance')

    if action_type == 'handover':
        target_assign_id = data.get('target_assign_id')
        if not target_assign_id:
            return jsonify({'status': 'F', 'msg': 'target_assign_id tidak ditemukan.'}), 400
        result = assignment_transaction.handover_pic_trx(sr_no, nik, int(target_assign_id))
    else:
        current_smk_id = data.get('current_smk_id')
        next_smk_id = data.get('next_smk_id')
        if not current_smk_id or not next_smk_id:
            return jsonify({'status': 'F', 'msg': 'current_smk_id atau next_smk_id tidak ditemukan.'}), 400
        result = workflow_transaction.advance_sr_phase(
            sr_no=sr_no,
            current_smk_id=int(current_smk_id),
            next_smk_id=int(next_smk_id),
            action_by=nik
        )

    if not result.get('status'):
        Log.warning(f'pic_workflow_action | SR: {sr_no} | NIK: {nik} | action: {action_type} | Msg: {result.get("msg")}')
        return jsonify({'status': 'F', 'msg': result.get('msg', 'Gagal.')}), 400

    Log.info(f'pic_workflow_action | SR: {sr_no} | NIK: {nik} | action: {action_type} | Berhasil')
    return jsonify({'status': 'T', 'msg': result.get('msg', 'Berhasil.')}), 200


@dashboard_bp.route('/myWork/detail/<path:sr_no>/assign', methods=['POST'])
@login_required
def submit_assignment(sr_no):
    """Submit assignment PIC dari halaman detail SR."""
    nik = session['user']['nik']

    result = assignment_transaction.submit_assignments_trx(sr_no, nik, request.form)

    if not result.get('status'):
        flash(result.get('msg', 'Gagal menyimpan assignment.'), 'error')
    else:
        flash(result.get('msg', 'Assignment berhasil disimpan.'), 'success')

    return redirect(url_for('owh_dashboard.sr_detail_view', sr_no=sr_no))


@dashboard_bp.route('/myWork/detail/<path:sr_no>/assign-sm', methods=['POST'])
@login_required
def submit_sm_assignment(sr_no):
    """IT GM assign IT SM pada SR, lalu advance 104→105."""
    nik = session['user']['nik']

    result = assignment_transaction.submit_sm_assignment_trx(sr_no, nik, request.form)

    if not result.get('status'):
        flash(result.get('msg', 'Gagal menyimpan assignment IT SM.'), 'error')
    else:
        flash(result.get('msg', 'IT SM berhasil di-assign.'), 'success')

    return redirect(url_for('owh_dashboard.sr_detail_view', sr_no=sr_no))

@dashboard_bp.route('/myWork/detail/<path:sr_no>/attachment', methods=['GET','POST'])
@login_required
def upload_attachment(sr_no):
    """Upload attachment dari halaman detail SR."""
    nik = session['user']['nik']
    file = request.files.get('attachment')

    if not file:
        flash('Tidak ada file yang diunggah.', 'error')
        return redirect(url_for('owh_dashboard.sr_detail_view', sr_no=sr_no))

    result = attachment_transaction.upload_attachment_trx(sr_no, nik, file)

    if not result.get('status'):
        flash(result.get('msg', 'Gagal mengunggah attachment.'), 'error')
    else:
        flash(result.get('msg', 'Attachment berhasil diunggah.'), 'success')

    return redirect(url_for('owh_dashboard.sr_detail_view', sr_no=sr_no))

@dashboard_bp.route('/myWork/detail/<path:sr_no>/view', methods=['GET'])
@login_required
def sr_detail_view(sr_no):
    """
    Halaman read-only detail SR.
    Konten SR dimuat via AJAX ke /api/get_sr_detail/<sr_no> (reuse existing API).
    View ini hanya menyiapkan shell page + data PMO form jika user adalah IT PMO.
    """
    clean_sr_no = urllib.parse.unquote(sr_no).strip()
    nik = session['user']['nik']

    # Cek apakah user adalah IT PMO — jika ya, siapkan data form reassign
    is_pmo = nik == workflow_transaction.IT_PM_NIK
    pmo_form_data = {}
    if is_pmo:
        from ..models import assignment_model
        from ..utils.converters import parse_rows
        picroles = parse_rows(assignment_model.get_assignable_picroles_model())
        assignable_role_ids = {r['it_role_id'] for r in picroles}
        all_assignments = assignment_transaction.get_all_assignments_trx(clean_sr_no)
        pmo_form_data = {
            'picroles': picroles,
            'it_users': parse_rows(assignment_model.get_it_users_model()),
            'current_assignments': [
                a for a in all_assignments if a.get('it_role_id') in assignable_role_ids
            ],
        }

    return render_template(
        '/page/sr_detail_view.html',
        user=session['user'],
        role=session['role'],
        active_menu='my_work',
        sr_no=clean_sr_no,
        is_pmo=is_pmo,
        pmo_form_data=pmo_form_data,
    )

@dashboard_bp.route('/myWork/detail/<path:sr_no>/pmo-reassign', methods=['POST'])
@login_required
def pmo_reassign(sr_no):
    """IT PMO meng-update assignment PIC pada SR di fase manapun."""
    nik = session['user']['nik']
    result = assignment_transaction.pmo_update_assign_trx(sr_no, nik, request.form)

    if not result.get('status'):
        flash(result.get('msg', 'Gagal memperbarui assignment.'), 'error')
    else:
        flash(result.get('msg', 'Assignment berhasil diperbarui.'), 'success')

    return redirect(url_for('owh_dashboard.sr_detail_view', sr_no=sr_no))


@dashboard_bp.route('/uploadDraft', methods=['GET', 'POST'])
@login_required
def uploadDraft_menu():
    return render_template('/page/upload_draft.html', user=session['user'], role=session['role'], active_menu='upload_draft')


@dashboard_bp.route('/approvedDraft', methods=['GET', 'POST'])
@login_required
def approvedDraft_menu():
    return render_template('/page/approved_draft.html', user=session['user'], role=session['role'], active_menu='approved_draft')


@dashboard_bp.route('/updateTimetable', methods=['GET', 'POST'])
@login_required
def updateTimetable_menu():
    return render_template('/page/update_timetable.html', user=session['user'], role=session['role'], active_menu='update_timetable')
