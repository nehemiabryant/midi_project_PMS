from flask import Blueprint, redirect, url_for
from ..helpers.decorators import login_required

assignment_bp = Blueprint('owh_assignment', __name__, url_prefix='/assignment', template_folder='../templates', static_folder='/static')


@assignment_bp.route('/<path:sr_no>', methods=['GET'])
@login_required
def assign_page(sr_no):
    """Redirect ke halaman detail SR di My Work."""
    return redirect(url_for('owh_dashboard.sr_detail_menu', sr_no=sr_no))
