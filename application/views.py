import os

from flask import (
    redirect, render_template, url_for, flash, jsonify, 
    Blueprint, request, session
)
# from flask_cors import cross_origin

# from config import MainConfig
from common.midiconnectserver.midilog import Logger

from . import transaction
from .helpers.login import validate_user_gateway
from .helpers.decorators import login_required
from .utils.converters import convert_to_dicts

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

#CREATESR
@owh_app.route('/createSR', methods=['GET', 'POST'])
@login_required
def createSR_menu():
    return render_template('/page/create_sr.html', user=session['user'], role=session['role'], active_menu='create_sr')

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

