import os
from flask import Flask, jsonify, render_template
from flask_wtf.csrf import CSRFProtect
from application.utils.date_utils import format_date_wib

from application.views.auth_view import auth_bp
from application.views.dashboard_view import dashboard_bp
from application.views.sr_view import sr_bp
from application.views.role_view import role_mgmt_bp
from application.views.task_view import task_bp
from application.views.assignment_view import assignment_bp
from application.views.karyawan_view import kry_bp

csrf = CSRFProtect()


def create_app(config_filename=None):
    app = Flask(__name__)

    app.secret_key = 'xk0asdf8@9*72201yp!7&-12sdf'

    if not config_filename:
        config_filename = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config.py'))

    app.config.from_object('config.MainConfig')

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(sr_bp)
    app.register_blueprint(role_mgmt_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(assignment_bp)
    app.register_blueprint(kry_bp)

    app.jinja_env.filters['format_date_wib'] = format_date_wib

    csrf.init_app(app)
    csrf.exempt(role_mgmt_bp)  # API JSON tidak memerlukan CSRF form token
    csrf.exempt(task_bp)       # Task API endpoint (JSON)

    # Error Handlers
    @app.errorhandler(400)
    def bad_request(e):
        return render_template(
            'page/error_page.html', 
            error_code="400", 
            error_title="Permintaan Tidak Valid",
            error_message="Server tidak dapat memproses permintaan dari client karena terdapat kesalahan pada permintaan."
        ), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template(
            'page/error_page.html', 
            error_code="403", 
            error_title="Akses Ditolak",
            error_message="Server menolak permintaan dari client karena client tidak memiliki akses yang diizinkan ke konten yang diminta."
        ), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template(
            'page/error_page.html', 
            error_code="404", 
            error_title="Halaman Tidak Ditemukan",
            error_message="Server tidak dapat menemukan konten yang diminta oleh client."
        ), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return render_template(
            'page/error_page.html', 
            error_code="405", 
            error_title="Metode Tidak Diizinkan",
            error_message="Server tidak dapat memproses permintaan dari client karena metode yang digunakan tidak diizinkan."
        ), 405

    @app.errorhandler(408)
    def request_timeout(e):
        return render_template(
            'page/error_page.html', 
            error_code="408", 
            error_title="Waktu Permintaan Habis",
            error_message="Server tidak dapat memproses permintaan dari client karena waktu permintaan telah habis."
        ), 408

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return render_template(
            'page/error_page.html', 
            error_code="413", 
            error_title="Data Terlalu Besar",
            error_message="Server tidak dapat memproses permintaan karena terlalu besar untuk server tangani."
        ), 413

    @app.errorhandler(415)
    def request_not_supported(e):
        return render_template(
            'page/error_page.html', 
            error_code="415", 
            error_title="Format Tidak Didukung",
            error_message="Tipe media tidak didukung oleh server."
        ), 415

    @app.errorhandler(429)
    def request_too_many(e):
        return render_template(
            'page/error_page.html', 
            error_code="429", 
            error_title="Terlalu Banyak Permintaan",
            error_message="Server menolak permintaan dari client karena terlalu banyak permintaan yang dilakukan dalam waktu yang singkat."
        ), 429

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template(
            'page/error_page.html', 
            error_code="500", 
            error_title="Kesalahan Server",
            error_message="Server mengalami kesalahan saat memproses permintaan dari client."
        ), 500

    return app
