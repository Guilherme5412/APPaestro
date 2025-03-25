import os
import pandas as pd
import io
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import streamlit as st

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_credentials():
    """
    Get or create credentials for Google Drive API.
    Prioritizes environment variables for service account credentials.
    Falls back to interactive OAuth flow if needed.
    
    Returns:
        Credentials: The Google API credentials
    """
    creds = None
    
    # Try to use service account credentials from environment variables
    if os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON'):
        try:
            service_account_info = json.loads(os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON'))
            creds = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=SCOPES)
            return creds
        except Exception as e:
            st.warning(f"Error loading service account credentials: {e}")
    
    # If service account credentials not available, try user credentials
    # Check if token.json exists
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_info(json.loads(
                open('token.json', 'r').read()), SCOPES)
        except Exception:
            pass
    
    # If no valid credentials available, we'll need to handle through the UI
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # In a Streamlit app, we need to handle the OAuth flow differently
            st.error("""
            Google Drive authentication is required but not configured.
            
            Please provide API credentials through environment variables or contact the administrator.
            """)
            # Provide a fallback for testing - create a download button
            st.info("In the meantime, you can download the file directly instead of using Google Drive.")
            raise Exception("Google Drive credentials not configured")
            
    return creds

def export_to_gdrive(df, filename, folder_name=None):
    """
    Export a DataFrame to Google Drive as a CSV file
    
    Args:
        df (pd.DataFrame): DataFrame to export
        filename (str): Name of the file to create
        folder_name (str, optional): Name of the folder to create or use
        
    Returns:
        str: URL to the created file
    """
    try:
        creds = get_credentials()
        service = build('drive', 'v3', credentials=creds)
        
        # Convert DataFrame to CSV
        csv_data = df.to_csv(index=False).encode('utf-8')
        csv_buffer = io.BytesIO(csv_data)
        
        # Prepare file metadata and media content
        file_metadata = {'name': filename}
        
        # Create or find folder if needed
        if folder_name:
            # Check if folder exists
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            
            if results.get('files', []):
                # Folder exists, use its ID
                folder_id = results['files'][0]['id']
            else:
                # Create folder
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = service.files().create(body=folder_metadata, fields='id').execute()
                folder_id = folder.get('id')
            
            # Set parent folder for the file
            file_metadata['parents'] = [folder_id]
        
        # Upload file
        media = MediaIoBaseUpload(csv_buffer, mimetype='text/csv', resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink',
            supportsAllDrives=True
        ).execute()
        
        # Make file readable by anyone with the link
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        service.permissions().create(fileId=file.get('id'), body=permission).execute()
        
        return file.get('webViewLink')
        
    except Exception as e:
        st.error(f"Error with Google Drive integration: {str(e)}")
        # For testing/development environment, provide a fallback
        csv_data = df.to_csv(index=False)
        st.download_button(
            "Download CSV (Google Drive export failed)",
            csv_data,
            filename,
            "text/csv",
            key='download-csv'
        )
        raise e
