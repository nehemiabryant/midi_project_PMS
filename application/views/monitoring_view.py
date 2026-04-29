from flask import Blueprint, redirect, render_template, url_for, flash, session, request, jsonify
from common.midiconnectserver.midilog import Logger
from application.transactions import my_work_transaction, sr_transaction, srlogs_transaction, workflow_transaction, attachment_transaction, assignment_transaction, task_transaction
from ..helpers.decorators import ajax_required, login_required, bypass_required
import urllib.parse

Log = Logger()

mnt_bp = Blueprint('owh_monitor', __name__, url_prefix='/monitoring', template_folder='../templates', static_folder='/static')

@mnt_bp.route('/by_SR', methods=['GET'])
@login_required
def monitoring_by_sr():
    years = sr_transaction.get_all_years_trx()
    quarters = sr_transaction.get_all_quarters_trx()
    categories = sr_transaction.get_all_categories_trx()
    departments = sr_transaction.get_all_departments_trx() 
    
    return render_template('/page/monitoring_by_sr.html', 
                           user=session.get('user'), 
                           role=session.get('role'), 
                           active_menu='monitoring_by_sr', 
                           years=years,
                           quarters=quarters,
                           categories=categories,
                           departments=departments)

@mnt_bp.route('/get_sr_no', methods=['GET'])
@login_required
@ajax_required
def api_monitoring_get_sr_no():
    filter_year = request.args.get('year')
    filter_q_id = request.args.get('q_id')
    filter_ctg_id = request.args.get('ctg_id')
    filter_midikriing = request.args.get('midikriing')

    db_result = sr_transaction.get_filtered_sr_no_trx(filter_year, filter_q_id, filter_ctg_id, filter_midikriing)
    if not db_result.get('status'):
        return jsonify({'status': False, 'msg': 'Failed to fetch data', 'sr_list': []}), 400
    
    return jsonify({'status': True, 'sr_list': db_result['data']['sr_list']})

@mnt_bp.route('/by_SR/get_cards', methods=['POST'])
@login_required
@ajax_required
def monitoring_by_sr_cards():
    req_data = request.get_json()

    sr_list = req_data.get('sr_nos', [])
    monitoring_counts = sr_transaction.get_monitoring_counts_trx(sr_list)

    return render_template('/partials/_monitoring_cards.html', monitoring_counts=monitoring_counts)

from flask import request, render_template

@mnt_bp.route('/by_SR/status_time', methods=['POST'])
@login_required
@ajax_required
def monitoring_by_sr_time():
    req_data = request.get_json()
    sr_list = req_data.get('sr_nos', [])

    trx_result = sr_transaction.get_monitoring_status_time_trx(sr_list)
    
    return render_template('/partials/_monitoring_time.html', 
                           chart_data=trx_result.get('data'))

@mnt_bp.route('/by_SR/status_overview', methods=['POST'])
@login_required
@ajax_required
def monitoring_by_sr_overview():
    req_data = request.get_json()
    sr_list = req_data.get('sr_nos', [])

    trx_result = sr_transaction.get_monitoring_status_overview_trx(sr_list)
    
    return render_template('/partials/_monitoring_overview.html', 
                           chart_data=trx_result.get('data'))

@mnt_bp.route('/by_SR/overdue_projects', methods=['POST'])
@login_required
@ajax_required
def monitoring_by_sr_overdue():
    req_data = request.get_json()
    sr_list = req_data.get('sr_nos', [])
    limit = req_data.get('limit', 50)
    offset = req_data.get('offset', 0)

    trx_result = sr_transaction.get_monitoring_overdue_projects_trx(sr_list, limit, offset)
    
    return render_template('/partials/_monitoring_overdue.html', 
                           items=trx_result.get('data'),
                           total_count=trx_result.get('total_count'))

@mnt_bp.route('/by_SR/completed_projects', methods=['POST'])
@login_required
@ajax_required
def monitoring_by_sr_completed():
    req_data = request.get_json()
    sr_list = req_data.get('sr_nos', [])
    limit = req_data.get('limit', 50)
    offset = req_data.get('offset', 0)

    trx_result = sr_transaction.get_monitoring_complete_projects_trx(sr_list, limit, offset)
    
    return render_template('/partials/_monitoring_completed.html', 
                           items=trx_result.get('data'),
                           total_count=trx_result.get('total_count'))

@mnt_bp.route('/by_SR/all_projects', methods=['POST'])
@login_required
@ajax_required
def monitoring_by_sr_project():
    req_data = request.get_json()
    sr_list = req_data.get('sr_nos', [])
    limit = req_data.get('limit', 50)
    offset = req_data.get('offset', 0)

    trx_result = sr_transaction.get_monitoring_all_projects_trx(sr_list, limit, offset)
    
    return render_template('/partials/_monitoring_project.html', 
                           items=trx_result.get('data'),
                           total_count=trx_result.get('total_count'))
