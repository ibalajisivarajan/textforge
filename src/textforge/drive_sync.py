import io
import json
import logging

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from .config import DRIVE_FILE_NAME, DRIVE_FOLDER
from .storage import load_snippets, save_snippets, _load_raw, _save_raw

log = logging.getLogger(__name__)


def get_drive_service(credentials):
    """Return authenticated Drive API service object."""
    return build("drive", "v3", credentials=credentials)


def find_snippets_file(service) -> str | None:
    """
    List files in appDataFolder with name == DRIVE_FILE_NAME.
    Return file ID if found, None otherwise.
    """
    try:
        resp = service.files().list(
            spaces=DRIVE_FOLDER,
            fields="files(id, name)",
            q=f"name='{DRIVE_FILE_NAME}'",
        ).execute()
        files = resp.get("files", [])
        return files[0]["id"] if files else None
    except Exception as e:
        log.warning("Error searching Drive for snippets file: %s", e)
        return None


def download_snippets(service, file_id: str) -> dict:
    """Download and parse snippets.json from Drive. Return parsed dict."""
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return json.loads(buf.getvalue().decode("utf-8"))


def upload_snippets(service, file_id: str | None, data: dict) -> str:
    """
    If file_id is None: create new file in appDataFolder.
    If file_id exists: update file content.
    Return file_id.
    """
    content = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype="application/json")

    if file_id is None:
        file_metadata = {
            "name": DRIVE_FILE_NAME,
            "parents": [DRIVE_FOLDER],
        }
        result = service.files().create(
            body=file_metadata, media_body=media, fields="id"
        ).execute()
        return result["id"]
    else:
        service.files().update(fileId=file_id, media_body=media).execute()
        return file_id


def sync_from_drive(credentials) -> bool:
    """
    Pull snippets from Drive → overwrite local cache.
    Return True on success, False on error.
    """
    try:
        service = get_drive_service(credentials)
        file_id = find_snippets_file(service)
        if file_id is None:
            log.info("No snippets file found on Drive; nothing to pull.")
            return True
        remote_data = download_snippets(service, file_id)
        _save_raw(remote_data)
        log.info("Synced snippets from Drive (%d snippets).", len(remote_data.get("snippets", [])))
        return True
    except Exception as e:
        log.warning("sync_from_drive failed: %s", e)
        return False


def sync_to_drive(credentials) -> bool:
    """
    Push local cache → Drive.
    Return True on success, False on error.
    """
    try:
        service = get_drive_service(credentials)
        file_id = find_snippets_file(service)
        local_data = _load_raw()
        if not local_data:
            log.info("Local snippets empty; skipping Drive upload.")
            return True
        upload_snippets(service, file_id, local_data)
        log.info("Synced local snippets to Drive.")
        return True
    except Exception as e:
        log.warning("sync_to_drive failed: %s", e)
        return False
