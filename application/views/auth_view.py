from flask import Blueprint, redirect, render_template, url_for, flash, session, request
from common.midiconnectserver.midilog import Logger
from ..helpers.login import validate_user_gateway
from ..helpers.decorators import login_required

Log = Logger()

auth_bp = Blueprint('owh_auth', __name__, url_prefix='/', template_folder='../templates', static_folder='/static')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    kd_menu = 'LOGIN'
    if request.method == 'POST':
        nik = request.form.get('nik', '').strip()
        password = request.form.get('password', '').strip()

        if not nik or not password:
            flash('NIK dan PIN harus diisi!')
            Log.error(f'{kd_menu} | Form validation failed | NIK: {nik}')
            return redirect(url_for('owh_auth.login'))

        hasilPin, error = validate_user_gateway(nik, password)

        if error:
            flash('Terjadi kesalahan sistem. Silakan coba lagi.')
            Log.error(f'{kd_menu} | Validate User Error | Error: {error}')
            return redirect(url_for('owh_auth.login'))

        if hasilPin != 'T':
            flash('NIK dan PIN Tidak Sesuai!')
            Log.warning(f'{kd_menu} | Invalid User Login | NIK: {nik}')
            return redirect(url_for('owh_auth.login'))

        return redirect(url_for('owh_dashboard.dashboard_menu'))
    else:
        return render_template('login.html')


@auth_bp.route('/logout', methods=['GET'])
def logout():
    if not session.get('user') or not session.get('role'):
        return redirect(url_for('owh_auth.login'))
    session.clear()
    return redirect(url_for('owh_auth.login'))
