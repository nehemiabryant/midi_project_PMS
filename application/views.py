import os

from flask import (
    redirect, render_template, url_for, flash, jsonify, 
    Blueprint, request, session
)
# from flask_cors import cross_origin

# from config import MainConfig
from common.midiconnectserver.midilog import Logger

from .transactions import sr_transaction
from .helpers.login import validate_user_gateway
from .helpers.decorators import login_required
from .utils.converters import convert_to_dicts
from .utils import tokenization

Log = Logger()

owh_app = Blueprint("owh",__name__, url_prefix='/', template_folder="templates", static_folder="/static")

@owh_app.route('/', methods=['GET'])
def main_redirect():
    return redirect(url_for('owh.dashboard_menu'))

@owh_app.route('/login', methods=['GET', 'POST'])
def login():
    kd_menu = 'LOGIN'
    if request.method == 'POST':
        nik = request.form.get('nik', '').strip()
        password = request.form.get('password', '').strip()
        
        if not nik or not password:
            flash('NIK dan PIN harus diisi!')
            Log.error(f'{kd_menu} | Form validation failed | NIK: {nik}')
            return redirect(url_for('owh.login'))
        
        hasilPin, error = validate_user_gateway(nik, password)

        if error:
            flash('Terjadi kesalahan sistem. Silakan coba lagi.')
            Log.error(f'{kd_menu} | Validate User Error | Error: {error}')
            return redirect(url_for('owh.login'))

        if hasilPin != 'T':
            flash('NIK dan PIN Tidak Sesuai!')
            Log.warning(f'{kd_menu} | Invalid User Login | NIK: {nik}')
            return redirect(url_for('owh.login'))
        
        user_data = session.get('user')
        nama = user_data.get('nama') if user_data else ''
        return redirect(url_for('owh.dashboard_menu'))
    else:
        return render_template('login.html')
    
#DASHBOARD   
@owh_app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard_menu():
    return render_template('/page/dashboard.html', user=session['user'], role=session['role'], active_menu='dashboard')

#LISTSR (NOW ONLY BEING USED IN DEVELOPMENT, WILL BE MOVED TO DASHBOARD WITH FILTERING FUNCTION LATER)
@owh_app.route('/listSR', methods=['GET'])
@login_required
def listSR_menu():
    sr_list = sr_transaction.get_all_sr_trx()
    
    if not sr_list.get('status'):
        flash(f"Error fetching Service Requests: {sr_list.get('msg')}", "error")
        sr_data = []
    else:
        sr_data = sr_list.get('data', [])

    return render_template('/page/list_sr.html', user=session['user'], role=session['role'], active_menu='list_sr', sr_data=sr_data)

#MYSR
@owh_app.route('/mySR', methods=['GET'])
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

#CREATESR
@owh_app.route('/createSR', methods=['GET', 'POST'])
@login_required
def createSR_menu():
    if request.method == 'POST':
        raw_form_data = request.form.to_dict()
        raw_form_data['requester'] = session.get('user', {}).get('nik', '')
        raw_form_data['divisi'] = session.get('user', {}).get('divisi', '')

        trx_result = sr_transaction.create_sr_trx(raw_form_data)

        if trx_result.get('status'):
            flash("Service Request created successfully!", "success")
            return redirect(url_for('owh.dashboard_menu'))
        else:
            flash(f"Error: {trx_result.get('msg')}", "error")
            return redirect(request.url) #ERROR PAGE IN PROGRESS

    return render_template('/page/create_sr.html', user=session['user'], role=session['role'], active_menu='create_sr')

#EDITSR
@owh_app.route('/editSR/<token>', methods=['GET', 'POST'])
@login_required
def editSR_menu(token):
    sr_no = tokenization.decrypt_token(token)

    if not sr_no:
        flash("Invalid or corrupted edit link.", "error")
        return redirect(url_for('owh.dashboard_menu'))
    
    current_user = session.get('user').get('nik', '')
    raw_form_data = request.form.to_dict()
    raw_form_data['requester'] = session.get('user', {}).get('nik', '')
    raw_form_data['divisi'] = session.get('user', {}).get('divisi', '')

    # 1. FETCH THE DATA FIRST
    # We must grab the SR before doing anything else so we know who owns it
    existing_sr_response = sr_transaction.get_edit_sr_trx(sr_no)
    
    # Check if the SR actually exists
    if not existing_sr_response.get('status') or not existing_sr_response.get('data'):
        flash("Service Request not found.", "error")
        return redirect(url_for('owh.dashboard_menu'))

    # Extract the single row of data 
    # (Assuming your fetch returns a list of dictionaries. Adjust the key if needed)
    sr_data = existing_sr_response['data'][0]
    
    # 2. THE AUTHORIZATION LOCK
    # 'req_id' is the column name we used in the INSERT query for the requester
    if sr_data.get('req_id') != current_user:
        # If you have an Admin role that SHOULD be able to edit everything, 
        # you can change the line above to:
        # if sr_data.get('req_id') != current_user and session.get('role') != 'Admin':
        
        flash("Unauthorized: You can only edit your own Service Requests.", "error")
        return redirect(url_for('owh.dashboard_menu'))

    # 3. PROCESS THE POST REQUEST (If they pass the lock)
    if request.method == 'POST':
        raw_form_data = request.form.to_dict()
        
        # We know they are the owner, so we can safely update
        trx_result = sr_transaction.update_sr_trx(raw_form_data, sr_no)

        if trx_result.get('status'):
            flash("Service Request updated successfully!", "success")
            return redirect(url_for('owh.dashboard_menu'))
        else:
            flash(f"Error: {trx_result.get('msg')}", "error")
            return redirect(request.url)

    # 4. RENDER THE GET REQUEST (If they pass the lock)
    return render_template('/page/create_sr.html', user=session['user'], role=session['role'], sr_data=sr_data)

#MYWORK
@owh_app.route('/myWork', methods=['GET', 'POST'])
@login_required
def myWork_menu():
    return render_template('/page/my_work.html', user=session['user'], role=session['role'], active_menu='my_work')

#UPLOADDRAFT
@owh_app.route('/uploadDraft', methods=['GET', 'POST'])
@login_required
def uploadDraft_menu():
    return render_template('/page/upload_draft.html', user=session['user'], role=session['role'], active_menu='upload_draft')

#APPROVEDDRAFT
@owh_app.route('/approvedDraft', methods=['GET', 'POST'])
@login_required
def approvedDraft_menu():
    return render_template('/page/approved_draft.html', user=session['user'], role=session['role'], active_menu='approved_draft')

#UPDATETIMETABLE
@owh_app.route('/updateTimetable', methods=['GET', 'POST'])
@login_required
def updateTimetable_menu():
    return render_template('/page/update_timetable.html', user=session['user'], role=session['role'], active_menu='update_timetable')
    
    
@owh_app.route('/logout', methods=['GET'])
def logout():
    if not session.get('user') or not session.get('role'):
        return redirect(url_for('owh.login'))
    user_data = session.get('user')
    user_role = session.get('role')
    nik = user_data.get('nik') if user_data else ''
    nama = user_data.get('nama') if user_data else ''
    session.clear()
    return redirect(url_for('owh.login'))

