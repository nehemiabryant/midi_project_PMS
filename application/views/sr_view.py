from flask import Blueprint, redirect, render_template, url_for, flash, session, request
from common.midiconnectserver.midilog import Logger
from ..transactions import sr_transaction
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
    current_user = session.get('user').get('nik', '')
    my_sr_list = sr_transaction.get_my_sr_trx(current_user)

    if not my_sr_list.get('status'):
        flash(f"Error fetching your Service Requests: {my_sr_list.get('msg')}", "error")
        sr_data = []
    else:
        sr_data = my_sr_list.get('data', [])

    return render_template('/page/my_sr.html', user=session['user'], role=session['role'], active_menu='my_sr', sr_data=sr_data)


@sr_bp.route('/createSR', methods=['GET', 'POST'])
@login_required
def createSR_menu():
    if request.method == 'POST':
        raw_form_data = request.form.to_dict()
        raw_form_data['requester'] = session.get('user', {}).get('nik', '')
        raw_form_data['divisi'] = session.get('user', {}).get('divisi', '')

        files = request.files

        trx_result = sr_transaction.create_sr_trx(raw_form_data, files)

        if trx_result.get('status'):
            flash("Service Request created successfully!", "success")
            return redirect(url_for('owh_dashboard.dashboard_menu'))
        else:
            flash(f"Error: {trx_result.get('msg')}", "error")
            return redirect(request.url)

    return render_template('/page/create_sr.html', user=session['user'], role=session['role'], active_menu='create_sr')


@sr_bp.route('/editSR/<token>', methods=['GET', 'POST'])
@login_required
def editSR_menu(token):
    sr_no = tokenization.decrypt_token(token)

    if not sr_no:
        flash("Invalid or corrupted edit link.", "error")
        return redirect(url_for('owh_dashboard.dashboard_menu'))

    current_user = session.get('user').get('nik', '')

    existing_sr_response = sr_transaction.get_edit_sr_trx(sr_no)

    if not existing_sr_response.get('status') or not existing_sr_response.get('data'):
        flash("Service Request not found.", "error")
        return redirect(url_for('owh_dashboard.dashboard_menu'))

    sr_data = existing_sr_response['data'][0]

    if sr_data.get('req_id') != current_user:
        flash("Unauthorized: You can only edit your own Service Requests.", "error")
        return redirect(url_for('owh_dashboard.dashboard_menu'))

    if request.method == 'POST':
        raw_form_data = request.form.to_dict()
        raw_form_data['requester'] = session.get('user', {}).get('nik', '')
        raw_form_data['divisi'] = session.get('user', {}).get('divisi', '')

        files = request.files

        trx_result = sr_transaction.update_sr_trx(raw_form_data, files, sr_no)

        if trx_result.get('status'):
            flash("Service Request updated successfully!", "success")
            return redirect(url_for('owh_dashboard.dashboard_menu'))
        else:
            flash(f"Error: {trx_result.get('msg')}", "error")
            return redirect(request.url)

    return render_template('/page/create_sr.html', user=session['user'], role=session['role'], sr_data=sr_data)
