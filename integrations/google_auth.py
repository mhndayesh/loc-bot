import os
import json
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("google_auth")

# If modifying these scopes, delete the file token.json.
# We consolidate all Google App scopes here so the user only authenticates once.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
]

class GoogleAuthManager:
    """
    Centralized Authentication Handler for all Google APIs.
    Reads credentials.json and generates/refreshes a universal token.json.
    """
    def __init__(self, token_path="token.json", creds_path="credentials.json"):
        self.token_path = token_path
        self.creds_path = creds_path
        self.creds = None
        
        # Load existing tokens if available
        if os.path.exists(self.token_path):
            try:
                self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                log.error(f"Failed to load existing token.json: {e}")
                self.creds = None

    def authenticate(self):
        """
        Ensures valid credentials exist. Triggers browser OAuth2 flow if missing or expired.
        """
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    log.info("Refreshing expired Google API token...")
                    self.creds.refresh(Request())
                except Exception as e:
                    log.error(f"Token refresh failed: {e}. Re-authenticating...")
                    self.creds = None
            
            if not self.creds:
                if not os.path.exists(self.creds_path):
                    log.error(f"Missing {self.creds_path}! Cannot authenticate Google APIs.")
                    log.error("Please download OAuth 2.0 Client credentials from the Google Cloud Console "
                              "and save it as 'credentials.json' in the root directory.")
                    return False
                
                log.info("Opening browser for Initial Google OAuth2 Authorization...")
                flow = InstalledAppFlow.from_client_secrets_file(self.creds_path, SCOPES)
                # This opens the user's browser for login
                self.creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())
                log.info(f"Saved new Google API token to {self.token_path}")
                
        return True

    def get_service(self, service_name, version):
        """
        Builds and returns a Google API service client.
        Example: get_service('gmail', 'v1')
        """
        if not self.authenticate():
            return None
            
        try:    
            return build(service_name, version, credentials=self.creds)
        except Exception as e:
            log.error(f"Failed to build Google service '{service_name}': {e}")
            return None

# Singleton instance for easy import across skills
auth_manager = GoogleAuthManager()
