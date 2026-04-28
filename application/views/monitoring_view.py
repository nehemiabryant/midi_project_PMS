from flask import Blueprint, redirect, render_template, url_for, flash, session, request, jsonify
from common.midiconnectserver.midilog import Logger
from application.transactions import my_work_transaction, sr_transaction, srlogs_transaction, workflow_transaction, attachment_transaction, assignment_transaction, task_transaction
from ..helpers.decorators import login_required, bypass_required
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
def api_monitoring_get_sr_no():
    filter_year = request.args.get('year')
    filter_q_id = request.args.get('q_id')
    filter_ctg_id = request.args.get('ctg_id')
    filter_midikriing = request.args.get('midikriing')

    db_result = sr_transaction.get_filtered_sr_no_trx(filter_year, filter_q_id, filter_ctg_id, filter_midikriing)
    return jsonify({'status': True, 'sr_list': db_result['data']['sr_list']})

@mnt_bp.route('/by_SR/get_cards', methods=['GET'])
@login_required
def monitoring_by_sr_cards():
    filter_year = request.args.get('year')
    filter_q_id = request.args.get('q_id')
    filter_ctg_id = request.args.get('ctg_id')
    filter_midikriing = request.args.get('midikriing')

    monitoring_counts = sr_transaction.get_monitoring_cards_trx(filter_year, filter_q_id, filter_ctg_id, filter_midikriing)

    return render_template('/partials/_monitoring_cards.html', 
                           user=session.get('user'), 
                           role=session.get('role'), 
                           active_menu='monitoring_by_sr', 
                           monitoring_counts=monitoring_counts)

@mnt_bp.route('/by_SR/time', methods=['GET'])
@login_required
def monitoring_by_sr_time():
    filter_year = request.args.get('year')
    filter_q_id = request.args.get('q_id')
    filter_ctg_id = request.args.get('ctg_id')
    filter_midikriing = request.args.get('midikriing')

    return render_template('/partials/_monitoring_time.html', 
                           user=session.get('user'), 
                           role=session.get('role'), 
                           active_menu='monitoring_by_sr')

@mnt_bp.route('/by_SR/overview', methods=['GET'])
@login_required
def monitoring_by_sr_overview():
    filter_year = request.args.get('year')
    filter_q_id = request.args.get('q_id')
    filter_ctg_id = request.args.get('ctg_id')
    filter_midikriing = request.args.get('midikriing')

    return render_template('/partials/_monitoring_overview.html', 
                           user=session.get('user'), 
                           role=session.get('role'), 
                           active_menu='monitoring_by_sr')

@mnt_bp.route('/by_SR/overdue', methods=['GET'])
@login_required
def monitoring_by_sr_overdue():
    filter_year = request.args.get('year')
    filter_q_id = request.args.get('q_id')
    filter_ctg_id = request.args.get('ctg_id')
    filter_midikriing = request.args.get('midikriing')

    return render_template('/partials/_monitoring_overdue.html', 
                           user=session.get('user'), 
                           role=session.get('role'), 
                           active_menu='monitoring_by_sr')

@mnt_bp.route('/by_SR/completed', methods=['GET'])
@login_required
def monitoring_by_sr_completed():
    filter_year = request.args.get('year')
    filter_q_id = request.args.get('q_id')
    filter_ctg_id = request.args.get('ctg_id')
    filter_midikriing = request.args.get('midikriing')

    return render_template('/partials/_monitoring_completed.html', 
                           user=session.get('user'), 
                           role=session.get('role'), 
                           active_menu='monitoring_by_sr')

@mnt_bp.route('/by_SR/project', methods=['GET'])
@login_required
def monitoring_by_sr_project():
    filter_year = request.args.get('year')
    filter_q_id = request.args.get('q_id')
    filter_ctg_id = request.args.get('ctg_id')
    filter_midikriing = request.args.get('midikriing')

    return render_template('/partials/_monitoring_project.html', 
                           user=session.get('user'), 
                           role=session.get('role'), 
                           active_menu='monitoring_by_sr')

