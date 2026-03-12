from common.midiconnectserver.midilog import Logger
from ..models import attachment_model
from ..helpers import pdf_upload as fu
import os
import uuid
from werkzeug.utils import secure_filename

Log = Logger()

def upload_and_record_files(reference_no: str, files_dict: dict, category_map: dict):
    """
    A modular uploader. You pass it the reference ID (sr_no), the files, 
    and a map telling it which HTML input matches which database category ID.
    """
    bucket_name = os.environ.get('R2_BUCKET_NAME')
    public_url_base = os.environ.get('R2_PUBLIC_URL')

    for field_name, ctg_id in category_map.items():
        file = files_dict.get(field_name)
        
        if file and file.filename:
            safe_filename = secure_filename(file.filename)
            unique_filename = f"{reference_no.replace('/', '_')}/{uuid.uuid4().hex}_{safe_filename}"
            
            try:
                fu.s3_client.upload_fileobj(
                    file, 
                    bucket_name, 
                    unique_filename,
                    ExtraArgs={'ContentType': 'application/pdf'}
                )
                file_url = f"{public_url_base}/{unique_filename}"
            except Exception as e:
                print(f"R2 Upload Failed for {field_name}: {str(e)}")
                continue 
            
            next_iter = attachment_model.get_next_iteration(reference_no, ctg_id)
            
            attach_params = {
                'sr_no': reference_no,
                'attach_ctg': ctg_id,
                'iteration': next_iter,
                'file_url': file_url
            }
            attachment_model.insert_attachment(attach_params)

def get_attachments_for_view(sr_no: str) -> dict:
    """Fetches the latest attachments and formats them into a clean dictionary."""
    db_result = attachment_model.get_latest_attachments(sr_no)
    
    if not db_result.get('status') or not db_result.get('data'):
        return {} # Return empty dict if no files exist

    headers = db_result['data'][0]
    rows = db_result['data'][1]

    # Turns the DB rows into a clean dictionary like: { 1: 'https://...', 2: 'https://...' }
    attachments = {}
    for row in rows:
        row_dict = dict(zip(headers, row))
        attachments[row_dict['attach_ctg']] = row_dict['file_url']
        
    return attachments