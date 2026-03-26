from common.midiconnectserver.midilog import Logger
from ..models import attachment_model
from ..helpers.pdf_upload import s3_client, BUCKET_NAME, PUBLIC_URL
from ..utils.converters import parse_rows
import os
import uuid
from werkzeug.utils import secure_filename

Log = Logger()

def upload_and_record_files(reference_no: str, files_dict: dict):
    """
    A modular uploader. You pass it the reference ID (sr_no), the files, 
    and a map telling it which HTML input matches which database category ID.
    """
    bucket_name = BUCKET_NAME
    public_url_base = PUBLIC_URL

    for field_name, file in files_dict.items():
        if field_name.startswith('attachment_ctg_') and file and file.filename:

            ctg_id = int(field_name.split('_')[-1])
        
        if file and file.filename:
            safe_filename = secure_filename(file.filename)
            unique_filename = f"{reference_no.replace('/', '_')}/{uuid.uuid4().hex}_{safe_filename}"
            
            try:
                s3_client.upload_fileobj(
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
    rows = parse_rows(db_result)
    if not rows:
        return {}

    return {row['attach_ctg']: row['file_url'] for row in rows}