from common.midiconnectserver.midilog import Logger
from ..models import attachment_model
from ..helpers.pdf_upload import s3_client, BUCKET_NAME, PUBLIC_URL
from ..utils.converters import parse_rows, convert_to_dicts
import os
import uuid
from ..helpers.pdf_thumbnail import generate_pdf_thumbnail
from werkzeug.utils import secure_filename

Log = Logger()

def upload_and_record_files(reference_no: str, files_dict: dict, current_smk_id: int, shared_conn=None):
    """
    A modular uploader. You pass it the reference ID (sr_no), the files, 
    and a map telling it which HTML input matches which database category ID.
    """
    bucket_name = BUCKET_NAME
    public_url_base = PUBLIC_URL

    docs_res = get_required_docs_for_phase_trx(current_smk_id, shared_conn)
    allowed_categories = [doc['attach_ctg'] for doc in docs_res.get('data', [])]

    for field_name, file in files_dict.items():
        if field_name.startswith('dynamic_doc_') and file and file.filename:

            ctg_str = field_name.split('_')[-1]
            if not ctg_str.isdigit():
                continue

            ctg_id = int(ctg_str)

            if ctg_id not in allowed_categories:
                continue
        
        if file and file.filename:
            safe_filename = secure_filename(file.filename)
            unique_filename = f"{reference_no.replace('/', '_')}/{uuid.uuid4().hex}_{safe_filename}"
            unique_thumb_name = f"{reference_no.replace('/', '_')}/thumb_{uuid.uuid4().hex}.jpg"
            
            try:
                # ==========================================
                # THE THUMBNAIL INTERCEPTOR
                # ==========================================
                # 1. Read the raw bytes from the Flask file object
                file_bytes = file.read()
                
                # 2. Generate the thumbnail!
                thumb_bytes = generate_pdf_thumbnail(file_bytes)
                
                # 3. CRITICAL: Rewind the file cursor so Boto3 can upload the PDF
                file.seek(0)

                s3_client.upload_fileobj(
                    file, 
                    bucket_name, 
                    unique_filename,
                    ExtraArgs={'ContentType': 'application/pdf'}
                )
                file_url = f"{public_url_base}/{unique_filename}"

                thumb_url = None
                if thumb_bytes:
                    s3_client.put_object(
                        Bucket=bucket_name, Key=unique_thumb_name, 
                        Body=thumb_bytes, ContentType='image/jpeg'
                    )
                    thumb_url = f"{public_url_base}/{unique_thumb_name}"

            except Exception as e:
                print(f"R2 Upload Failed for {field_name}: {str(e)}")
                continue 
            
            next_iter = attachment_model.get_next_iteration(reference_no, ctg_id, shared_conn)
            
            attach_params = {
                'sr_no': reference_no,
                'attach_ctg': ctg_id,
                'iteration': next_iter,
                'file_url': file_url,
                'thumbnail_url': thumb_url
            }
            attachment_model.insert_attachment(attach_params, shared_conn)

def get_latest_attachments_trx(sr_no: str, shared_conn=None) -> dict:
    """Fetches the latest attachments and formats them into a clean dictionary."""
    db_result = attachment_model.get_latest_attachments(sr_no, shared_conn)
    rows = parse_rows(db_result)
    if not rows:
        return {}

    return {
        row['attach_ctg']: {
            'file_url': row['file_url'],
            'thumbnail_url': row['thumbnail_url'],
            'attach_details': row['attach_details']
        } 
        for row in rows
    }

# In attachment_transaction.py
def get_attachments_for_view(sr_no: str, shared_conn=None) -> list:
    """
    Fetches attachments and formats them as a clean list of dictionaries for Jinja.
    Returns: [{'attach_ctg': 1, 'attach_details': 'Alur Proses', 'file_url': 'https...'}]
    """
    try:
        db_result = attachment_model.get_latest_attachments(sr_no, shared_conn)
        
        if not db_result.get('status') or not db_result.get('data') or len(db_result['data']) < 2:
            return [] # Return an empty list safely if no docs exist
            
        headers = db_result['data'][0]
        rows = db_result['data'][1]
        
        return convert_to_dicts(rows, headers)
        
    except Exception as e:
        Log.error(f"Exception | Get Attachments View | Msg: {str(e)}")
        return []

def get_required_docs_for_phase_trx(current_smk_id: int, shared_conn=None) -> dict:
    """Transaction wrapper for fetching required documents for a given phase."""
    try:
        db_result = attachment_model.get_required_docs_for_phase(current_smk_id, shared_conn)
        
        # If the database query itself failed
        if not db_result.get('status'):
            return {'status': False, 'data': [], 'msg': db_result.get('msg', 'Database error')}

        rows = parse_rows(db_result)
        
        # If the query succeeded, but there are no mandatory documents for this phase
        if not rows:
            return {'status': True, 'data': [], 'msg': 'No mandatory documents required.'}

        # If it found documents, return them neatly packaged!
        return {'status': True, 'data': rows, 'msg': 'Required documents fetched successfully.'}
        
    except Exception as e:
        Log.error(f"Exception | Get Required Docs Trx | Msg: {str(e)}")
        return {'status': False, 'data': [], 'msg': 'An internal error occurred.'}