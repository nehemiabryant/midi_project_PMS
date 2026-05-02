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

        return redirect(url_for('owh_dashboard.myWork_menu'))

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
    action_type = request.form.get('action_type', 'advance')

    if action_type == 'handover':
        target_assign_id = request.form.get('target_assign_id')
        if not target_assign_id:
            flash('target_assign_id tidak ditemukan.', 'error')
            return redirect(url_for('owh_dashboard.sr_detail_pic', sr_no=sr_no))
        result = assignment_transaction.handover_pic_trx(sr_no, nik, int(target_assign_id))
    else:
        current_smk_id = request.form.get('current_smk_id')
        next_smk_id = request.form.get('next_smk_id')
        if not current_smk_id or not next_smk_id:
            flash('Data aksi tidak lengkap.', 'error')
            return redirect(url_for('owh_dashboard.sr_detail_pic', sr_no=sr_no))
        result = workflow_transaction.advance_sr_phase(
            sr_no=sr_no,
            current_smk_id=int(current_smk_id),
            next_smk_id=int(next_smk_id),
            action_by=nik
        )

    if not result.get('status'):
        Log.warning(f'pic_workflow_action | SR: {sr_no} | NIK: {nik} | action: {action_type} | Msg: {result.get("msg")}')
        flash(result.get('msg', 'Gagal.'), 'error')
        return redirect(url_for('owh_dashboard.sr_detail_pic', sr_no=sr_no))

    Log.info(f'pic_workflow_action | SR: {sr_no} | NIK: {nik} | action: {action_type} | Berhasil')
    flash(result.get('msg', 'Status SR berhasil dilanjutkan.'), 'success')
    return redirect(url_for('owh_dashboard.myWork_menu'))


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

@dashboard_bp.route('/sr/view/<path:sr_no>', methods=['GET'])
@login_required
def sr_detail_view(sr_no):
    clean_sr_no = urllib.parse.unquote(sr_no).strip()
    back_url = request.args.get('back', url_for('owh_dashboard.myWork_menu'))

    return render_template(
        '/page/sr_detail_view.html',
        user=session['user'],
        role=session['role'],
        active_menu=None,
        sr_no=clean_sr_no,
        back_url=back_url,
    )

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
