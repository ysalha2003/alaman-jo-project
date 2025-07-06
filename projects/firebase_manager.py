# firebase_manager.py for projects app
# Simplified version to avoid import errors during initial setup

import json
import logging

logger = logging.getLogger(__name__)

class FirebaseRemoteConfigManager:
    """Firebase Remote Config Manager for Django integration"""
    
    def __init__(self, project_id, keyfile_json):
        self.PROJECT_ID = project_id
        self.KEYFILE_JSON = keyfile_json
        self.access_token = None
        self.etag = None
        self.config = None
        logger.info(f"Firebase manager initialized for project: {project_id}")

    def _get_access_token(self):
        """Get access token from service account credentials"""
        try:
            # Try to import required libraries
            from oauth2client.service_account import ServiceAccountCredentials
            
            if isinstance(self.KEYFILE_JSON, str):
                keyfile_dict = json.loads(self.KEYFILE_JSON)
            else:
                keyfile_dict = self.KEYFILE_JSON
                
            SCOPES = ['https://www.googleapis.com/auth/firebase.remoteconfig']
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(keyfile_dict, SCOPES)
            access_token_info = credentials.get_access_token()
            return access_token_info.access_token
        except ImportError:
            logger.error("oauth2client not installed. Run: pip install oauth2client")
            return None
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            return None

    def _get(self):
        """Retrieve the current Remote Config template"""
        try:
            import requests
            
            if not self.access_token:
                self.access_token = self._get_access_token()
                if not self.access_token:
                    return False
            
            BASE_URL = 'https://firebaseremoteconfig.googleapis.com'
            REMOTE_CONFIG_ENDPOINT = f'v1/projects/{self.PROJECT_ID}/remoteConfig'
            REMOTE_CONFIG_URL = f'{BASE_URL}/{REMOTE_CONFIG_ENDPOINT}'
            
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            resp = requests.get(REMOTE_CONFIG_URL, headers=headers, timeout=30)
            
            if resp.status_code == 200:
                self.config = resp.json()
                self.etag = resp.headers.get('ETag')
                logger.info('Retrieved template has been loaded into memory.')
                return True
            else:
                logger.error(f'Unable to get template: {resp.text}')
                return False
        except ImportError:
            logger.error("requests library not installed. Run: pip install requests")
            return False
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return False

    def _publish(self):
        """Publish local template to Firebase server"""
        try:
            import requests
            
            if not self.config or not self.etag:
                logger.error("No config or etag available for publishing")
                return False
            
            BASE_URL = 'https://firebaseremoteconfig.googleapis.com'
            REMOTE_CONFIG_ENDPOINT = f'v1/projects/{self.PROJECT_ID}/remoteConfig'
            REMOTE_CONFIG_URL = f'{BASE_URL}/{REMOTE_CONFIG_ENDPOINT}'
                
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json; UTF-8',
                'If-Match': self.etag
            }
            
            resp = requests.put(
                REMOTE_CONFIG_URL, 
                data=json.dumps(self.config).encode('utf-8'), 
                headers=headers,
                timeout=30
            )
            
            if resp.status_code == 200:
                logger.info('Template has been published.')
                self.etag = resp.headers.get('ETag')
                return True
            else:
                logger.error(f'Unable to publish template: {resp.text}')
                return False
        except Exception as e:
            logger.error(f"Publish request failed: {e}")
            return False

    def get_default_value(self):
        """Get the default value from the current configuration"""
        if self.config and 'parameters' in self.config:
            try:
                default_value = self.config["parameters"]["activity"]["defaultValue"]["value"]
                return default_value
            except KeyError:
                logger.warning("'activity' parameter not found in config")
                return None
        else:
            logger.error("Configuration not loaded or invalid.")
            return None
        
    def set_new_value(self, new_value):
        """Set a new value for the defaultValue in the current configuration"""
        if self.config and 'parameters' in self.config:
            try:
                if 'activity' not in self.config['parameters']:
                    # Create the activity parameter if it doesn't exist
                    self.config['parameters']['activity'] = {
                        'defaultValue': {'value': new_value}
                    }
                else:
                    self.config["parameters"]["activity"]["defaultValue"]["value"] = new_value
                
                logger.info(f'Set new default value: {new_value}')
                return True
            except Exception as e:
                logger.error(f"Failed to set new value: {e}")
                return False
        else:
            logger.error("Configuration not loaded.")
            return False

    def update_remote_config(self, new_url):
        """Complete workflow to update remote config with new URL"""
        try:
            # Get current config
            if not self._get():
                return False, "Failed to retrieve current config"
            
            # Set new value
            if not self.set_new_value(new_url):
                return False, "Failed to set new value"
            
            # Publish changes
            if not self._publish():
                return False, "Failed to publish changes"
            
            return True, "Successfully updated remote config"
            
        except Exception as e:
            logger.error(f"Error updating remote config: {e}")
            return False, f"Error: {e}"