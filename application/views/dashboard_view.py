from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from application.transactions import sr_transaction, my_work_transaction, assignment_transaction, workflow_transaction, attachment_transaction
from ..helpers.decorators import login_required

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


@dashboard_bp.route('/myWork/detail/<path:sr_no>', methods=['GET', 'POST'])
@login_required
def sr_detail_menu(sr_no):
    """Halaman detail SR — termasuk section assignment untuk IT SM."""
    nik = session['user']['nik']
    result = my_work_transaction.get_sr_detail_trx(sr_no, nik)

    if not result.get('status'):
        flash(result.get('msg', 'Gagal memuat detail SR.'), 'error')
        return redirect(url_for('owh_dashboard.myWork_menu'))

    page_data = result['data']
    sr_detail = page_data.get('sr_detail', {})

    is_pic = page_data.get('is_pic')
    is_sm = page_data.get('is_sm')
    is_gm = page_data.get('is_gm')

    current_smk_id = sr_detail.get('smk_id')

    docs_res = attachment_transaction.get_required_docs_for_phase_trx(current_smk_id)
    required_docs = docs_res.get('data', [])

    current_files_dict = attachment_transaction.get_latest_attachments_trx(sr_no)

    if request.method == 'POST':
        # Security: Only PICs can upload
        if is_pic and not is_sm and not is_gm:
            # Capture the entire files dictionary because inputs are named dynamically 
            # e.g., 'dynamic_doc_BRD', 'dynamic_doc_UAT'
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
        else:
            flash('Anda tidak memiliki otorisasi untuk mengunggah file.', 'error')

        return redirect(url_for('owh_dashboard.sr_detail_menu', sr_no=sr_no))

    # PIC (SCM/DEV/QA/RO) yang bukan SM/GM → render detail_pic.html
    if is_pic and not is_sm and not is_gm:
        
        return render_template(
            '/page/detail_pic.html',
            user=session['user'],
            role=session['role'],
            active_menu='my_work',
            sr_detail=page_data['sr_detail'],
            user_roles=page_data['user_roles'],
            pic_sections=page_data['pic_sections'],
            required_docs=required_docs,
            current_files=current_files_dict
        )

    # IT GM dan IT SM → render detail_sr.html (template bersama dengan kondisi is_gm/is_sm)
    return render_template(
        '/page/detail_sr.html',
        user=session['user'],
        role=session['role'],
        active_menu='my_work',
        sr_detail=page_data['sr_detail'],
        user_roles=page_data['user_roles'],
        all_assignments=page_data['all_assignments'],
        assignments_by_role=page_data['assignments_by_role'],
        is_sm=page_data['is_sm'],
        is_gm=page_data['is_gm'],
        can_assign=page_data['can_assign'],
        can_assign_sm=page_data['can_assign_sm'],
        assignment_data=page_data['assignment_data'],
        gm_assign_data=page_data['gm_assign_data'],
    )


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

    return redirect(url_for('owh_dashboard.sr_detail_menu', sr_no=sr_no))


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

    return redirect(url_for('owh_dashboard.sr_detail_menu', sr_no=sr_no))

@dashboard_bp.route('/myWork/detail/<path:sr_no>/attachment', methods=['GET','POST'])
@login_required
def upload_attachment(sr_no):
    """Upload attachment dari halaman detail SR."""
    nik = session['user']['nik']
    file = request.files.get('attachment')

    if not file:
        flash('Tidak ada file yang diunggah.', 'error')
        return redirect(url_for('owh_dashboard.sr_detail_menu', sr_no=sr_no))

    result = attachment_transaction.upload_attachment_trx(sr_no, nik, file)

    if not result.get('status'):
        flash(result.get('msg', 'Gagal mengunggah attachment.'), 'error')
    else:
        flash(result.get('msg', 'Attachment berhasil diunggah.'), 'success')

    return redirect(url_for('owh_dashboard.sr_detail_menu', sr_no=sr_no))

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
