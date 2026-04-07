from flask import Blueprint, redirect, render_template, url_for, flash, session, request
from common.midiconnectserver.midilog import Logger
from application.transactions import my_work_transaction, sr_transaction, srlogs_transaction, workflow_transaction, attachment_transaction
from ..helpers.decorators import login_required

Log = Logger()

sr_bp = Blueprint('owh_sr', __name__, url_prefix='/', template_folder='../templates', static_folder='/static')


@sr_bp.route('/', methods=['GET'])
def main_redirect():
    return redirect(url_for('owh_dashboard.dashboard_menu'))


@sr_bp.route('/listSR', methods=['GET'])
@login_required
def listSR_menu():
    sr_list = sr_transaction.get_all_sr_trx()

    if not sr_list.get('status'):
        flash(f"Error fetching Service Requests: {sr_list.get('msg')}", "error")
        sr_data = []
    else:
        sr_data = sr_list.get('data', [])

    return render_template('/page/list_sr.html', user=session['user'], role=session['role'], active_menu='list_sr', sr_data=sr_data)

@sr_bp.route('/createSR', methods=['GET', 'POST'])
@login_required
def createSR_menu():
    docs_res = attachment_transaction.get_required_docs_for_phase_trx(101)
    ui_doc_blueprints = docs_res.get('data', [])

    current_files_dict = {}

    if request.method == 'POST':
        raw_form_data = request.form.to_dict()

        maker_id = session.get('user', {}).get('nik', '')
        raw_form_data['maker_id'] = maker_id

        files = request.files

        trx_result = sr_transaction.create_sr_trx(raw_form_data, files)

        if trx_result.get('status'):
            new_sr_no = trx_result['data'][0][0]

            # 2. Pack the data for the very first log
            genesis_log_data = {
                'sr_no': new_sr_no,
                'smk_id': 101,
                'action_by': maker_id    
            }

            log_result = srlogs_transaction.create_sr_log_trx(genesis_log_data)

            if log_result.get('status'):
                flash("Service Request created successfully!", "success")
            else:
                flash(f"SR Saved, but workflow error: {log_result.get('msg')}", "warning")

            return redirect(url_for('owh_dashboard.myWork_menu'))
        else:
            flash(f"Error: {trx_result.get('msg')}", "error")
            return redirect(request.url)

    return render_template('/page/sr_form.html', user=session.get('user'), role=session.get('role'), active_menu='create_sr'
                           , required_docs=ui_doc_blueprints, current_files=current_files_dict)


@sr_bp.route('/editSR/<path:sr_no>', methods=['GET', 'POST'])
@login_required
def editSR_menu(sr_no):
    if not sr_no:
        flash("Invalid or corrupted edit link.", "error")
        return redirect(url_for('owh_dashboard.dashboard_menu'))

    current_user = session.get('user', {}).get('nik', '')

    eligibility_result = workflow_transaction.authorize_sr_access(
        sr_no=sr_no, 
        user_nik=current_user,
        intent='EDIT'
    )

    if not eligibility_result.get('status'):
        #error_msg = eligibility_result.get('msg', 'Access denied.')
        #flash(error_msg, 'error') 
        flash(eligibility_result.get('msg'), "error")
        
        return redirect(url_for('owh_dashboard.dashboard_menu'))

    sr_data = eligibility_result['data'][0]
    current_smk_id = sr_data.get('smk_id', 101)

    docs_res = attachment_transaction.get_required_docs_for_phase_trx(current_smk_id)
    ui_doc_blueprints = docs_res.get('data', [])

    current_files_dict = sr_data.get('attachments', {})

    if sr_data.get('req_id') != current_user:
        flash("Unauthorized: You can only edit your own Service Requests.", "error")
        return redirect(url_for('owh_dashboard.dashboard_menu'))

    if request.method == 'POST':
        raw_form_data = request.form.to_dict()

        files = request.files

        trx_result = sr_transaction.update_sr_trx(raw_form_data, files, sr_no, current_smk_id)

        if trx_result.get('status'):
            flash("Service Request updated successfully!", "success")
            return redirect(url_for('owh_dashboard.dashboard_menu'))
        else:
            flash(f"Error: {trx_result.get('msg')}", "error")
            return redirect(request.url)

    return render_template('/page/sr_form.html', mode='edit', user=session.get('user'), role=session.get('role'), active_menu='my_sr'
                           , sr_data=sr_data, required_docs=ui_doc_blueprints, current_files=current_files_dict)

@sr_bp.route('/editSR/<path:sr_no>/confirm', methods=['POST'])
@login_required
def confirmSR_menu(sr_no):
    current_user = session.get('user', {}).get('nik', '')

    eligibility_result = workflow_transaction.authorize_sr_access(
        sr_no=sr_no,
        user_nik=current_user,
        intent='EDIT'
    )

    if not eligibility_result.get('status'):
        flash(eligibility_result.get('msg'), "error")
        return redirect(url_for('owh_dashboard.myWork_menu'))

    sr_data = eligibility_result['data'][0]

    if sr_data.get('req_id') != current_user:
        flash("Hanya requester yang dapat mengkonfirmasi SR ini.", "error")
        return redirect(url_for('owh_sr.editSR_menu', sr_no=sr_no))

    if sr_data.get('smk_id') != 101:
        flash("SR ini sudah tidak dalam status Draft.", "warning")
        return redirect(url_for('owh_dashboard.myWork_menu'))

    advance_result = workflow_transaction.advance_sr_phase(
        sr_no=sr_no,
        current_smk_id=101,
        next_smk_id=102,
        action_by=current_user
    )

    if advance_result.get('status'):
        flash("SR berhasil dikonfirmasi dan diteruskan ke atasan.", "success")
        return redirect(url_for('owh_dashboard.myWork_menu'))
    else:
        flash(advance_result.get('msg', 'Gagal mengkonfirmasi SR.'), "error")
        return redirect(url_for('owh_sr.editSR_menu', sr_no=sr_no))


@sr_bp.route('/approval/<path:sr_no>', methods=['GET', 'POST'])
@login_required
def approveSR_menu(sr_no):

    if not sr_no:
        flash("Invalid or corrupted approval link.", "error")
        return redirect(url_for('owh_dashboard.dashboard_menu'))
    
    current_user = session.get('user', {}).get('nik', '')
    
    # 1. Bouncer Check (Checks if they have the right to view AND approve)
    if not my_work_transaction.can_approve_sr_trx(sr_no, current_user).get('status'):
        flash('You do not have permission to view this SR.', 'error')
        return redirect(url_for('owh_dashboard.myWork_menu'))

    # 2. Eligibility Check (Ensures it is their turn in the workflow)
    eligibility_result = workflow_transaction.authorize_sr_access(
        sr_no=sr_no,
        user_nik=current_user,
        intent='APPROVE'
    )

    if not eligibility_result.get('status'):
        flash(eligibility_result.get('msg'), "error")
        return redirect(url_for('owh_dashboard.myWork_menu'))

    sr_data = eligibility_result['data'][0]
    current_smk_id = sr_data.get('smk_id') 
    
    current_files_dict = attachment_transaction.get_attachments_for_view(sr_no)
    options = workflow_transaction.get_dropdown_options(current_smk_id)
    
    if request.method == 'POST':
        # ONLY process the workflow advancement. No data updates.
        next_smk_id = int(request.form.get('intended_next_smk_id'))
        
        advance_result = workflow_transaction.advance_sr_phase(
            sr_no=sr_no,
            current_smk_id=current_smk_id,
            next_smk_id=next_smk_id,
            action_by=current_user
        )

        if advance_result.get('status'):
            flash("Service Request updated and approved successfully!", "success")
            return redirect(url_for('owh_dashboard.dashboard_menu'))
        else:
            flash(f"Approval failed: {advance_result.get('msg')}", "error")
            return redirect(request.url)

    # Pointing to the new read-only approval template
    return render_template('/page/sr_approve.html', 
                           user=session.get('user'), 
                           role=session.get('role'), 
                           active_menu='my_work',
                           sr_data=sr_data, 
                           options=options, 
                           current_files=current_files_dict)

@sr_bp.route('/project_details/<string:phase_name>', defaults={'sr_no': None}, methods=['GET'])
@sr_bp.route('/project_details/<string:phase_name>/<path:sr_no>', methods=['GET'])
@login_required
def project_details_menu(phase_name, sr_no):
    sr_list = sr_transaction.get_srs_by_phase_trx(phase_name)
    
    return render_template('/page/project_detail.html', user=session['user'], role=session['role'], active_menu='dashboard',
        phase_name=phase_name, sr_list=sr_list, current_sr_no=sr_no)

#BEING KEPT AS A REFERENCE IN CASE SOMETHING GOES WRONG
@sr_bp.route('/projectDetails-design/<path:sr_no>', methods=['GET'])
@login_required
def project_details_design_menu(sr_no):
    # Jika token dari sidebar (biasanya string 'token' atau kosong), BYPASS pencarian DB
    if not sr_no:
        # Langsung render HTML tanpa mencari ke database
        return render_template('page/project_detail_design.html', 
                               user=session.get('user', {}), 
                               role=session.get('role'), 
                               active_menu='project_details',
                               sr_no='SR-TESTING-001') # Data dummy

    # Logika asli Anda untuk mendekripsi token dan mencari ke database...
    
    # ... (Kode pencarian API/Database Anda) ...
    # Pastikan jika API gagal, jangan `return jsonify(api_response)`. 
    # Tapi gunakan `flash` dan `redirect` seperti ini:
    
    # if not response.get('status'):
    #     flash("Data tidak ditemukan", "error")
    #     return redirect(url_for('owh_dashboard.dashboard_menu'))

    return render_template('page/project_detail_design.html', 
                           user=session.get('user', {}), 
                           role=session.get('role'), 
                           active_menu='project_details',
                           sr_no=sr_no)

@sr_bp.route('/api/get_sr_detail/<path:sr_no>', methods=['GET'])
@login_required
def api_get_sr_detail(sr_no):
    sr_data = sr_transaction.get_sr_detail_trx(sr_no)
    
    if not sr_data:
        flash("Invalid or corrupted link.", "error")
        return redirect(url_for('owh_dashboard.dashboard_menu'))
    
    current_files_dict = attachment_transaction.get_attachments_for_view(sr_no)

    return render_template('/partials/_sr_detail_content.html', sr=sr_data, current_files_dict=current_files_dict)