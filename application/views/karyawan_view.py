from flask import Blueprint, jsonify, request
from ..transactions import karyawan_transaction
from ..helpers.decorators import login_required, ajax_required

kry_bp = Blueprint('kry_bp', __name__)

@kry_bp.route('/karyawan/search', methods=['GET'])
@login_required
@ajax_required
def search_karyawan():
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 5, type=int)
    offset = request.args.get('offset', 0, type=int)

    result = karyawan_transaction.search_karyawan_trx(query, limit, offset)
    if not result.get('status'):
        return jsonify({'error': 'server_error', 'details': result.get('msg')}), 500
    return jsonify({'data': result.get('data')}), 200