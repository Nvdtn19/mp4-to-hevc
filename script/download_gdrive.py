# download_gdrive.py
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import io

def main():
    FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID")
    # Paths are relative to the current working directory of the script execution (usually GITHUB_WORKSPACE)
    DOWNLOAD_DIR_NAME = "temp_downloads"
    SERVICE_ACCOUNT_FILE = os.path.join(DOWNLOAD_DIR_NAME, "service_account_key.json")
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    DOWNLOAD_DIR = os.path.join(os.getcwd(), DOWNLOAD_DIR_NAME)
    FILES_LIST_PATH = os.path.join(os.getcwd(), "files_to_upload.txt")

    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        
        service = build('drive', 'v3', credentials=credentials)

        try:
            folder_metadata = service.files().get(fileId=FOLDER_ID, fields='name').execute()
            print(f"Attempting to download from Google Drive folder: {folder_metadata.get('name')}") # Adjusted single quotes for clarity
        except HttpError as error:
            print(f"Error retrieving folder metadata: {error}")
            print(f"Make sure the service account has Viewer access to folder ID: {FOLDER_ID}")
            exit(1)

        query = f"'{FOLDER_ID}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            fields='files(id, name, mimeType, size)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        items = results.get('files', [])

        if not items:
            print('No files found in the folder.')
        else:
            print(f'Found {len(items)} files.')
            downloaded_files_count = 0
            with open(FILES_LIST_PATH, 'w') as f_list:
                for item in items:
                    file_id = item['id']
                    file_name = item['name']
                    mime_type = item['mimeType']
                    
                    print(f'Downloading: {file_name} (ID: {file_id}, MimeType: {mime_type})')

                    request = service.files().get_media(fileId=file_id)
                    
                    output_file_name = file_name
                    if 'google-apps' in mime_type:
                        if 'document' in mime_type:
                            request = service.files().export_media(fileId=file_id, mimeType='application/pdf')
                            output_file_name += '.pdf'
                        elif 'spreadsheet' in mime_type:
                            request = service.files().export_media(fileId=file_id, mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                            output_file_name += '.xlsx'
                        elif 'presentation' in mime_type:
                            request = service.files().export_media(fileId=file_id, mimeType='application/pdf')
                            output_file_name += '.pdf'
                        else:
                            print(f'Warning: Skipping Google Workspace file {file_name} with unhandled mimeType: {mime_type}')
                            continue
                    
                    full_path = os.path.join(DOWNLOAD_DIR, output_file_name)
                    fh = io.FileIO(full_path, 'wb')
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                    print(f'Successfully downloaded: {file_name}')
                    f_list.write(f'{full_path}\n')
                    downloaded_files_count += 1
                print(f'Finished downloading {downloaded_files_count} files.')

    except HttpError as error:
        print(f'An API error occurred: {error}')
        print('Please ensure:')
        print('1. The Google Drive API is enabled in your Google Cloud Project.')
        print('2. Your GCP_SERVICE_ACCOUNT_KEY secret contains the correct JSON content.')
        print('3. The Service Account email has "Viewer" access to the Google Drive folder.')
        exit(1)
    except Exception as e:
        print(f'An unexpected error occurred: {e}')
        exit(1)

if __name__ == "__main__":
    main()