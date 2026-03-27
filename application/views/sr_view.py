from flask import Blueprint, redirect, render_template, url_for, flash, session, request
from common.midiconnectserver.midilog import Logger
from ..transactions import sr_transaction, srlogs_transaction, workflow_transaction
from ..helpers.decorators import login_required
from ..utils import tokenization

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

@sr_bp.route('/mySR', methods=['GET'])
@login_required
def mySR_menu():
    current_user = session.get('user', {}).get('nik', '') 
    my_sr_list = sr_transaction.get_my_sr_trx(current_user)

    if not my_sr_list.get('status'):
        flash(f"Error fetching your Service Requests: {my_sr_list.get('msg')}", "error")
        sr_data = []
    else:
        sr_data = my_sr_list.get('data', [])

    return render_template('/page/my_sr.html', user=session.get('user'), role=session.get('role'), active_menu='my_sr', sr_data=sr_data)

@sr_bp.route('/createSR', methods=['GET', 'POST'])
@login_required
def createSR_menu():
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

            return redirect(url_for('owh_sr.mySR_menu'))
        else:
            flash(f"Error: {trx_result.get('msg')}", "error")
            return redirect(request.url)

    return render_template('/page/create_sr.html', user=session.get('user'), role=session.get('role'), active_menu='create_sr')


@sr_bp.route('/editSR/<token>', methods=['GET', 'POST'])
@login_required
def editSR_menu(token):
    sr_no = tokenization.decrypt_token(token)

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

    if sr_data.get('req_id') != current_user:
        flash("Unauthorized: You can only edit your own Service Requests.", "error")
        return redirect(url_for('owh_dashboard.dashboard_menu'))

    if request.method == 'POST':
        raw_form_data = request.form.to_dict()

        files = request.files

        trx_result = sr_transaction.update_sr_trx(raw_form_data, files, sr_no)

        if trx_result.get('status'):
            flash("Service Request updated successfully!", "success")
            return redirect(url_for('owh_dashboard.dashboard_menu'))
        else:
            flash(f"Error: {trx_result.get('msg')}", "error")
            return redirect(request.url)

    return render_template('/page/create_sr.html', user=session.get('user'), role=session.get('role'), active_menu='my_sr', sr_data=sr_data)

@sr_bp.route('/approval/<token>', methods=['GET', 'POST'])
@login_required
def approveSR_menu(token):
    sr_no = tokenization.decrypt_token(token)

    if not sr_no:
        flash("Invalid or corrupted approval link.", "error")
        return redirect(url_for('owh_dashboard.dashboard_menu'))

    current_user = session.get('user', {}).get('nik', '')

    # 1. Eligibility Check (Reused perfectly!)
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

    options = workflow_transaction.get_dropdown_options(current_smk_id)
    

    if request.method == 'POST':
        raw_form_data = request.form.to_dict()
        files = request.files

        # ==========================================
        # PART A: UPDATE THE EDITABLE DATA
        # ==========================================
        trx_result = sr_transaction.update_sr_trx(raw_form_data, files, sr_no)

        if not trx_result.get('status'):
            flash(f"Error saving data: {trx_result.get('msg')}", "error")
            return redirect(request.url)

        # ==========================================
        # PART B: FIGURE OUT THE WORKFLOW STATE
        # ==========================================
        next_smk_id = int(request.form.get('intended_next_smk_id'))
        
        # ==========================================
        # PART C: ADVANCE THE PHASE
        # ==========================================
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
            flash(f"Data saved, but phase failed to advance: {advance_result.get('msg')}", "warning")
            return redirect(request.url)

    return render_template('/page/approve_sr.html', user=session.get('user'), role=session.get('role'), active_menu='my_work', sr_data=sr_data, options=options)

@sr_bp.route('/projectDetails/<token>', methods=['GET'])
@login_required
def project_details_menu(token):
    # Jika token dari sidebar (biasanya string 'token' atau kosong), BYPASS pencarian DB
    if token == 'token' or not token:
        # Langsung render HTML tanpa mencari ke database
        return render_template('page/project_detail.html', 
                               user=session.get('user', {}), 
                               role=session.get('role'), 
                               active_menu='project_details',
                               sr_no='SR-TESTING-001') # Data dummy

    # Logika asli Anda untuk mendekripsi token dan mencari ke database...
    sr_no = tokenization.decrypt_token(token)
    
    # ... (Kode pencarian API/Database Anda) ...
    # Pastikan jika API gagal, jangan `return jsonify(api_response)`. 
    # Tapi gunakan `flash` dan `redirect` seperti ini:
    
    # if not response.get('status'):
    #     flash("Data tidak ditemukan", "error")
    #     return redirect(url_for('owh_dashboard.dashboard_menu'))

    return render_template('page/project_detail.html', 
                           user=session.get('user', {}), 
                           role=session.get('role'), 
                           active_menu='project_details',
                           sr_no=sr_no)