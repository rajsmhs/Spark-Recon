import configparser
from pathlib import Path

def get_aws_credentials():
    """
    Simple function to read AWS credentials for default profile
    Returns access key, secret key, and region
    """
    try:
        # Get credentials file path
        credentials_path = str(Path.home() / '.aws' / 'credentials')
        
        # Read credentials
        config = configparser.ConfigParser()
        config.read(credentials_path)
        
        # Get default profile credentials
        access_key = config.get('default', 'aws_access_key_id', fallback=None)
        secret_key = config.get('default', 'aws_secret_access_key', fallback=None)
        region = config.get('default', 'region', fallback=None)
        
        return {
            'access_key': access_key,
            'secret_key': secret_key,
            'region': region
        }

    except Exception as e:
        print(f"Error reading AWS credentials: {str(e)}")
        return None
