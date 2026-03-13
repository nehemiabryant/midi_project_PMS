import os
import boto3

def get_cfg_value(target_key: str) -> str:
    """Reads the same Connection.cfg file your database uses."""
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'common', 'midiconnectserver', 'config', 'Connection.cfg'))
    if not os.path.exists(cfg_path):
        print(f"CRITICAL: Could not find config file at {cfg_path}")
        return ""

    with open(cfg_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            # NEW: Handle both '=' and spaces cleanly
            if "=" in line:
                parts = line.split("=", 1)
            else:
                parts = line.split(None, 1)
                
            # NEW: Use .strip() to remove any accidental trailing spaces
            if len(parts) == 2 and parts[0].strip() == target_key:
                return parts[1].strip()
                
    print(f"CRITICAL: Key '{target_key}' not found in config file!")
    return ""

# Initialize the client using your config file!
s3_client = boto3.client(
    's3',
    endpoint_url=get_cfg_value('R2_ENDPOINT_URL'),
    aws_access_key_id=get_cfg_value('R2_ACCESS_KEY_ID'),
    aws_secret_access_key=get_cfg_value('R2_SECRET_ACCESS_KEY')
)

# You can also export these so your transaction file can use them
BUCKET_NAME = get_cfg_value('R2_BUCKET_NAME')
PUBLIC_URL = get_cfg_value('R2_PUBLIC_URL')