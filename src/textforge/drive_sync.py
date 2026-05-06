import io
import json
import logging

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from .config import DRIVE_FILE_NAME, DRIVE_FOLDER
from .storage import _load_raw, _save_raw

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
    Create or update snippets.json in Drive appDataFolder.
    Returns the file ID.
    """
    content = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype="application/json")

    if file_id is None:
        result = service.files().create(
            body={"name": DRIVE_FILE_NAME, "parents": [DRIVE_FOLDER]},
            media_body=media,
            fields="id",
        ).execute()
        return result["id"]
    else:
        service.files().update(fileId=file_id, media_body=media).execute()
        return file_id


def sync_from_drive(credentials) -> bool:
    """
    Pull snippets from Drive → overwrite local cache.
    Returns True on success, False on any error.
    """
    if credentials is None:
        log.debug("sync_from_drive: no credentials, skipping.")
        return False
    try:
        service = get_drive_service(credentials)
        file_id = find_snippets_file(service)
        if file_id is None:
            log.info("No snippets file on Drive — nothing to pull.")
            return True
        remote_data = download_snippets(service, file_id)
        _save_raw(remote_data)
        log.info("Pulled %d snippets from Drive.", len(remote_data.get("snippets", [])))
        return True
    except Exception as e:
        log.warning("sync_from_drive failed: %s", e)
        return False


def sync_to_drive(credentials) -> bool:
    """
    Push local cache → Drive.
    Returns True on success, False on any error.
    """
    if credentials is None:
        log.debug("sync_to_drive: no credentials, skipping.")
        return False
    try:
        local_data = _load_raw()
        if not local_data:
            log.info("Local snippets empty — skipping Drive upload.")
            return True
        service = get_drive_service(credentials)
        file_id = find_snippets_file(service)
        upload_snippets(service, file_id, local_data)
        log.info("Pushed %d snippets to Drive.", len(local_data.get("snippets", [])))
        return True
    except Exception as e:
        log.warning("sync_to_drive failed: %s", e)
        return False
