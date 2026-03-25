from flask import Blueprint, jsonify, request, session
from ..helpers.decorators import login_required
from ..transactions import task_transaction
from common.midiconnectserver.midilog import Logger

Log = Logger()

task_bp = Blueprint('owh_task', __name__, url_prefix='/task')


@task_bp.route('/list/<path:sr_no>', methods=['GET'])
@login_required
def get_tasks(sr_no):
    """List semua task pada SR untuk picrole user yang login."""
    nik = session['user']['nik']
    result = task_transaction.get_tasks_trx(sr_no, nik)

    if not result.get('status'):
        return jsonify({'status': 'F', 'data': [], 'msg': result.get('msg')}), 403

    return jsonify({'status': 'T', 'data': result.get('data', [])}), 200

@task_bp.route('/create/<path:sr_no>', methods=['POST'])
@login_required
def create_task(sr_no):
    """Buat task baru pada SR."""
    nik = session['user']['nik']
    data = request.get_json(silent=True) or {}

    result = task_transaction.create_task_trx(sr_no, nik, data)

    if not result.get('status'):
        return jsonify({'status': 'F', 'data': [], 'msg': result.get('msg')}), 400

    return jsonify({'status': 'T', 'data': result.get('data', []), 'msg': result.get('msg')}), 201

@task_bp.route('/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    """Update task yang sudah ada."""
    nik = session['user']['nik']
    data = request.get_json(silent=True) or {}

    result = task_transaction.update_task_trx(task_id, nik, data)

    if not result.get('status'):
        return jsonify({'status': 'F', 'data': [], 'msg': result.get('msg')}), 400

    return jsonify({'status': 'T', 'data': result.get('data', []), 'msg': result.get('msg')}), 200


@task_bp.route('/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    """Hapus task."""
    nik = session['user']['nik']

    result = task_transaction.delete_task_trx(task_id, nik)

    if not result.get('status'):
        return jsonify({'status': 'F', 'data': [], 'msg': result.get('msg')}), 400

    return jsonify({'status': 'T', 'data': [], 'msg': result.get('msg')}), 200
