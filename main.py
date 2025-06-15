#!/usr/bin/env python3
"""
Dropbox to Google Drive Migration Tool

このツールは、DropboxからGoogle Drive（共有ドライブ対応）へ
ファイルを効率的に移行するためのPythonアプリケーションです。

主な機能:
- ファイル・フォルダ構造の完全保持
- Google Workspace共有ドライブ対応
- 共有設定の詳細表示と移行
- 認証トークンの自動管理
- 堅牢なエラーハンドリングとリトライ機能

使用方法:
    python main.py [OPTIONS]

オプション:
    --test      テストモード（/testフォルダのみ移行）
    --dry-run   ドライラン（実際の移行なし）
    --verbose   詳細ログ表示
    --config    設定ファイルのパス（デフォルト: config.json）

必要な環境変数:
    GOOGLE_CLIENT_ID: Google Cloud Console で取得
    GOOGLE_CLIENT_SECRET: Google Cloud Console で取得
    DROPBOX_APP_KEY: Dropbox App Console で取得
    DROPBOX_APP_SECRET: Dropbox App Console で取得

Author: Generated with Claude Code
Version: 1.0.0
"""

import asyncio
import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import timezone

import dropbox
from dropbox.exceptions import ApiError
from dropbox.files import FileMetadata
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from tqdm import tqdm
from dotenv import load_dotenv
import pickle
import io
import mimetypes

# 環境変数の読み込み
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Google Drive OAuth2 scopes
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]


class MigrationTool:
    """
    DropboxからGoogle Driveへのファイル移行を行うメインクラス

    このクラスは、Dropboxの認証、Google Driveの認証、ファイルの移行、
    共有設定の移行、エラーハンドリングなど、移行に必要な全ての機能を提供します。

    Attributes:
        config (Dict[str, Any]): 設定ファイル（config.json）の内容
        dry_run (bool): ドライランモード（実際の移行を行わない）
        test_mode (bool): テストモード（限定フォルダのみ移行）
        dropbox_client (dropbox.Dropbox): Dropbox APIクライアント
        drive_service: Google Drive APIサービス
        folder_map (Dict[str, str]): DropboxパスとGoogle DriveフォルダIDのマッピング
        shared_drive_id (Optional[str]): 共有ドライブのID

    Example:
        config = load_config("config.json")
        tool = MigrationTool(config, dry_run=False, test_mode=True)
        asyncio.run(tool.migrate())
    """

    def __init__(
        self, config: Dict[str, Any], dry_run: bool = False, test_mode: bool = False
    ):
        """
        MigrationToolインスタンスを初期化

        Args:
            config: 設定ファイルの内容
            dry_run: Trueの場合、実際のファイル移行は行わない
            test_mode: Trueの場合、テストフォルダのみを対象とする
        """
        self.config = config
        self.dry_run = dry_run
        self.test_mode = test_mode
        self.dropbox_client = None
        self.drive_service = None
        self.folder_map = {}  # DropboxパスとGoogle DriveフォルダIDのマッピング

        # Initialize logs directory
        Path("logs").mkdir(exist_ok=True)

        # Add file handler for logging
        if not dry_run:
            fh = logging.FileHandler("logs/migration.log", mode="a")
            fh.setLevel(logging.INFO)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            fh.setFormatter(formatter)
            logger.addHandler(fh)

    def authenticate_dropbox(self) -> dropbox.Dropbox:
        """
        Dropbox OAuth2認証を実行してクライアントを返す

        保存済みのトークンがあれば再利用し、無効な場合は再認証を行います。
        必要なスコープ: files.metadata.read, files.content.read, sharing.read, account_info.read

        Returns:
            dropbox.Dropbox: 認証済みのDropboxクライアント

        Raises:
            Exception: 認証に失敗した場合
        """
        app_key = os.getenv("DROPBOX_APP_KEY")
        app_secret = os.getenv("DROPBOX_APP_SECRET")
        token_path = "dropbox_token.pickle"

        # Try to load existing token
        if os.path.exists(token_path):
            try:
                with open(token_path, "rb") as token_file:
                    token_data = pickle.load(token_file)
                    # Test if token is still valid
                    dbx = dropbox.Dropbox(token_data["access_token"])
                    dbx.users_get_current_account()
                    logger.info("Using saved Dropbox token")
                    return dbx
            except Exception as e:
                logger.info(f"Saved token invalid, re-authenticating: {e}")
                os.remove(token_path)

        # Simple OAuth2 flow for Dropbox with required scopes
        auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(
            app_key,
            consumer_secret=app_secret,
            token_access_type="offline",
            scope=[
                "files.metadata.read",
                "files.content.read",
                "sharing.read",
                "account_info.read",
            ],
        )

        authorize_url = auth_flow.start()
        print(f"\n1. Go to: {authorize_url}")
        print("2. Click 'Allow' (you might have to log in first)")
        print("3. Copy the authorization code.")

        try:
            auth_code = input("Enter the authorization code here: ").strip()
        except EOFError:
            logger.error(
                "No input available for authorization code. Run in interactive mode."
            )
            raise

        try:
            oauth_result = auth_flow.finish(auth_code)

            # Save token for future use
            token_data = {
                "access_token": oauth_result.access_token,
                "refresh_token": oauth_result.refresh_token,
            }
            with open(token_path, "wb") as token_file:
                pickle.dump(token_data, token_file)

            return dropbox.Dropbox(oauth_result.access_token)
        except Exception as e:
            logger.error(f"Error authenticating Dropbox: {e}")
            raise

    def authenticate_google_drive(self):
        """
        Google Drive OAuth2認証を実行してサービスクライアントを返す

        保存済みのトークンがあれば再利用し、無効な場合は再認証を行います。
        必要なスコープ: drive.file, drive（共有ドライブアクセス用）

        Returns:
            googleapiclient.discovery.Resource: 認証済みのGoogle Drive APIサービス

        Raises:
            Exception: 認証に失敗した場合
        """
        creds = None
        token_path = "token.pickle"

        # Token file stores the user's access and refresh tokens
        if os.path.exists(token_path):
            with open(token_path, "rb") as token:
                creds = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_config(
                    {
                        "installed": {
                            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                            "redirect_uris": [
                                "urn:ietf:wg:oauth:2.0:oob",
                                "http://localhost",
                            ],
                        }
                    },
                    SCOPES,
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(token_path, "wb") as token:
                pickle.dump(creds, token)

        return build("drive", "v3", credentials=creds)

    def setup_authentication(self):
        """Setup authentication for both services."""
        logger.info("Setting up authentication...")

        # Authenticate Dropbox
        logger.info("Authenticating with Dropbox...")
        self.dropbox_client = self.authenticate_dropbox()

        # Test Dropbox connection
        try:
            account = self.dropbox_client.users_get_current_account()
            logger.info(f"Successfully authenticated Dropbox as: {account.email}")
        except Exception as e:
            logger.error(f"Failed to authenticate Dropbox: {e}")
            raise

        # Authenticate Google Drive
        logger.info("Authenticating with Google Drive...")
        self.drive_service = self.authenticate_google_drive()

        # Test Google Drive connection
        try:
            about = self.drive_service.about().get(fields="user").execute()
            logger.info(
                f"Successfully authenticated Google Drive as: {about['user']['emailAddress']}"
            )
        except Exception as e:
            logger.error(f"Failed to authenticate Google Drive: {e}")
            raise

    def create_folder_in_drive(
        self, folder_name: str, parent_id: Optional[str] = None
    ) -> str:
        """Create a folder in Google Drive and return its ID."""
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }

        if parent_id:
            file_metadata["parents"] = [parent_id]

        if self.dry_run:
            logger.info(f"[DRY RUN] Would create folder: {folder_name}")
            return f"dry-run-folder-{folder_name}"

        try:
            # Add shared drive support if needed
            create_params = {"body": file_metadata, "fields": "id"}

            if hasattr(self, "shared_drive_id") and self.shared_drive_id:
                create_params["supportsAllDrives"] = True

            folder = self.drive_service.files().create(**create_params).execute()
            return folder.get("id")
        except Exception as e:
            logger.error(f"Error creating folder {folder_name}: {e}")
            raise

    def get_shared_drive_id(self, drive_name: str) -> Optional[str]:
        """Get the ID of a shared drive by name."""
        try:
            results = (
                self.drive_service.drives()
                .list(pageSize=100, fields="drives(id, name)")
                .execute()
            )

            drives = results.get("drives", [])
            for drive in drives:
                if drive["name"] == drive_name:
                    drive_id = drive["id"]
                    # Validate the drive ID by trying to access it
                    try:
                        self.drive_service.files().list(
                            driveId=drive_id,
                            corpora="drive",
                            includeItemsFromAllDrives=True,
                            supportsAllDrives=True,
                            pageSize=1,
                        ).execute()
                        logger.info(
                            f"Found and verified shared drive: {drive_name} (ID: {drive_id})"
                        )
                        return drive_id
                    except Exception as verify_error:
                        logger.error(
                            f"Shared drive {drive_name} exists but cannot be accessed: {verify_error}"
                        )
                        return None

            logger.warning(f"Shared drive '{drive_name}' not found")
            return None
        except Exception as e:
            logger.error(f"Error searching for shared drive: {e}")
            return None

    def ensure_folder_structure(self, dropbox_path: str) -> str:
        """Ensure the folder structure exists in Google Drive and return the folder ID."""
        # Normalize path for consistent mapping
        normalized_path = str(Path(dropbox_path)).replace("\\", "/")
        if normalized_path in self.folder_map:
            return self.folder_map[normalized_path]

        parts = Path(dropbox_path).parts[1:]  # Remove leading '/'
        current_parent = None
        current_path = ""

        # Check if using shared drive
        dest_config = self.config["destination"]
        if dest_config.get("use_shared_drive", False):
            shared_drive_name = dest_config.get("shared_drive_name", "01_Logomix")
            shared_drive_id = self.get_shared_drive_id(shared_drive_name)

            if shared_drive_id:
                # Use shared drive as root
                current_parent = shared_drive_id
                self.shared_drive_id = shared_drive_id
                logger.info(f"Using shared drive '{shared_drive_name}' as destination")
            else:
                logger.error(
                    f"Shared drive '{shared_drive_name}' not found. Using My Drive instead."
                )

        # Get or create destination root folder
        dest_root = dest_config["root_folder"].strip("/")
        if dest_root:
            if dest_root not in self.folder_map:
                # Check if folder exists
                query = f"name='{dest_root}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
                if current_parent:
                    query += f" and '{current_parent}' in parents"

                # Add shared drive support
                kwargs = {"q": query, "fields": "files(id, name)"}
                if hasattr(self, "shared_drive_id"):
                    kwargs.update(
                        {
                            "corpora": "drive",
                            "driveId": self.shared_drive_id,
                            "includeItemsFromAllDrives": True,
                            "supportsAllDrives": True,
                        }
                    )

                results = self.drive_service.files().list(**kwargs).execute()

                items = results.get("files", [])
                if items:
                    self.folder_map[dest_root] = items[0]["id"]
                else:
                    self.folder_map[dest_root] = self.create_folder_in_drive(
                        dest_root, current_parent
                    )

            current_parent = self.folder_map[dest_root]
            current_path = dest_root

        # Create nested folder structure
        for part in parts[:-1]:  # Exclude the file name
            current_path = f"{current_path}/{part}" if current_path else part

            if current_path not in self.folder_map:
                # Check if folder exists
                query = f"name='{part}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
                if current_parent:
                    query += f" and '{current_parent}' in parents"

                # Add shared drive support for folder search
                search_kwargs = {"q": query, "fields": "files(id, name)"}
                if hasattr(self, "shared_drive_id") and self.shared_drive_id:
                    search_kwargs.update(
                        {
                            "corpora": "drive",
                            "driveId": self.shared_drive_id,
                            "includeItemsFromAllDrives": True,
                            "supportsAllDrives": True,
                        }
                    )

                results = self.drive_service.files().list(**search_kwargs).execute()

                items = results.get("files", [])
                if items:
                    folder_id = items[0]["id"]
                    logger.debug(f"Found existing folder '{part}': {folder_id}")
                else:
                    folder_id = self.create_folder_in_drive(part, current_parent)
                    logger.debug(f"Created new folder '{part}': {folder_id}")

                self.folder_map[current_path] = folder_id
                self.folder_map[normalized_path] = (
                    folder_id  # Also store normalized path
                )

            current_parent = self.folder_map[current_path]

        # Store the final mapping with normalized path
        self.folder_map[normalized_path] = current_parent
        return current_parent

    def upload_file_to_drive(
        self,
        file_path: str,
        file_data: bytes,
        dropbox_metadata: FileMetadata,
        metadata_dict: Dict[str, Any] = None,
    ):
        """Upload a file to Google Drive."""
        try:
            # Get parent folder ID
            parent_id = self.ensure_folder_structure(file_path)

            # Prepare file metadata
            file_metadata = {"name": Path(file_path).name}

            if parent_id:
                file_metadata["parents"] = [parent_id]

            # Set modified time if available
            if hasattr(dropbox_metadata, "client_modified"):
                # Google Drive API requires RFC 3339 format with timezone
                modified_time = dropbox_metadata.client_modified
                if modified_time.tzinfo is None:
                    # Add UTC timezone if not present
                    modified_time = modified_time.replace(tzinfo=timezone.utc)

                # Format as RFC 3339 (ISO 8601 with timezone)
                file_metadata["modifiedTime"] = modified_time.isoformat()

            if self.dry_run:
                logger.info(
                    f"[DRY RUN] Would upload: {file_path} ({len(file_data)} bytes)"
                )
                return

            # Upload file
            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = "application/octet-stream"

            media = MediaIoBaseUpload(
                io.BytesIO(file_data), mimetype=mime_type, resumable=True
            )

            # Add shared drive support if needed
            create_params = {"body": file_metadata, "media_body": media, "fields": "id"}

            if hasattr(self, "shared_drive_id") and self.shared_drive_id:
                create_params["supportsAllDrives"] = True

            request = self.drive_service.files().create(**create_params)

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.debug(f"Upload progress: {int(status.progress() * 100)}%")

            file_id = response.get("id")
            logger.info(
                f"Successfully uploaded: {file_path} (Google Drive ID: {file_id})"
            )

            # Apply sharing permissions if available
            if (
                metadata_dict
                and metadata_dict.get("sharing", {}).get("is_shared")
                and self.config["options"].get("migrate_permissions", True)
            ):
                self.apply_sharing_permissions(file_id, metadata_dict["sharing"])

            return file_id

        except Exception as e:
            logger.error(f"Error uploading {file_path}: {e}")
            raise

    def get_file_sharing_info(self, file_id: str) -> Dict[str, Any]:
        """
        Dropboxファイルの共有情報を取得

        Args:
            file_id: DropboxファイルのID

        Returns:
            Dict[str, Any]: 共有情報辞書
                - is_shared (bool): 共有されているかどうか
                - permissions (List[Dict]): 権限リスト（email, role, can_edit）
                - access_type (str): アクセスタイプ

        Note:
            共有されていないファイルや取得エラーの場合は、is_shared=Falseを返します。
        """
        try:
            # Get sharing info
            sharing_info = self.dropbox_client.sharing_get_file_metadata(file_id)

            permissions = []
            if hasattr(sharing_info, "users"):
                for user_perm in sharing_info.users:
                    permissions.append(
                        {
                            "email": (
                                user_perm.user.email
                                if hasattr(user_perm.user, "email")
                                else "Unknown"
                            ),
                            "role": (
                                str(user_perm.role)
                                if hasattr(user_perm, "role")
                                else "Unknown"
                            ),
                            "can_edit": getattr(user_perm, "can_edit", False),
                        }
                    )

            return {
                "is_shared": True,
                "permissions": permissions,
                "access_type": (
                    str(sharing_info.access_type)
                    if hasattr(sharing_info, "access_type")
                    else "Unknown"
                ),
            }
        except Exception as e:
            logger.debug(f"No sharing info or error getting sharing info: {e}")
            return {"is_shared": False, "permissions": [], "access_type": "private"}

    def apply_sharing_permissions(
        self, file_id: str, sharing_info: Dict[str, Any]
    ) -> None:
        """
        Google DriveファイルにDropboxの共有権限を適用

        Args:
            file_id: Google DriveファイルのID
            sharing_info: get_file_sharing_info()で取得した共有情報

        Note:
            Dropboxの権限をGoogle Drive権限にマッピング:
            - edit権限 → writer
            - view権限 → reader
            - comment権限 → commenter
            - その他 → reader（デフォルト）
        """
        if not sharing_info.get("is_shared") or not sharing_info.get("permissions"):
            return

        logger.info(f"Applying sharing permissions to file {file_id}")

        for perm in sharing_info["permissions"]:
            try:
                # Map Dropbox roles to Google Drive roles

                # Extract role from Dropbox permission
                dropbox_role = perm.get("role", "").lower()
                if "edit" in dropbox_role:
                    google_role = "writer"
                elif "view" in dropbox_role:
                    google_role = "reader"
                elif "comment" in dropbox_role:
                    google_role = "commenter"
                else:
                    google_role = "reader"  # Default to reader

                permission = {
                    "type": "user",
                    "role": google_role,
                    "emailAddress": perm.get("email"),
                }

                if self.dry_run:
                    logger.info(
                        f"[DRY RUN] Would share with {perm.get('email')} as {google_role}"
                    )
                else:
                    self.drive_service.permissions().create(
                        fileId=file_id, body=permission, sendNotificationEmail=False
                    ).execute()
                    logger.info(f"Shared with {perm.get('email')} as {google_role}")

            except Exception as e:
                logger.error(f"Failed to share with {perm.get('email')}: {e}")

    def list_files_in_folder(self, folder_path: str = "") -> List[tuple]:
        """List all files in a Dropbox folder recursively with metadata."""
        files = []

        try:
            # If test mode, limit to specific folder or use root with limit
            if self.test_mode:
                test_folder = self.config.get("test_folder", "/test")
                logger.info(f"TEST MODE: Checking for test folder {test_folder}")

                # Try to list test folder first
                try:
                    result = self.dropbox_client.files_list_folder(
                        test_folder, recursive=True
                    )
                    folder_path = test_folder
                    logger.info(
                        f"TEST MODE: Found test folder, processing files in {folder_path}"
                    )
                except ApiError as e:
                    if e.error.is_path() and e.error.get_path().is_not_found():
                        logger.info(
                            f"TEST MODE: Test folder not found, using root folder with limit"
                        )
                        folder_path = ""
                        result = self.dropbox_client.files_list_folder(
                            folder_path, recursive=True
                        )
                    else:
                        raise
            else:
                result = self.dropbox_client.files_list_folder(
                    folder_path, recursive=True
                )

            while True:
                for entry in result.entries:
                    if isinstance(entry, FileMetadata):
                        # Get additional metadata
                        metadata_dict = {
                            "name": entry.name,
                            "path": entry.path_display,
                            "size": entry.size,
                            "modified": (
                                entry.client_modified.isoformat()
                                if hasattr(entry, "client_modified")
                                else None
                            ),
                            "rev": entry.rev,
                            "id": entry.id,
                        }

                        # Log file details
                        logger.info(f"Found file: {entry.path_display}")
                        logger.info(f"  - Size: {entry.size:,} bytes")
                        logger.info(f"  - Modified: {metadata_dict['modified']}")
                        logger.info(f"  - File ID: {entry.id}")

                        # Get sharing info if migrate_permissions is enabled
                        if self.config["options"].get("migrate_permissions", True):
                            sharing_info = self.get_file_sharing_info(entry.id)
                            metadata_dict["sharing"] = sharing_info
                            if sharing_info["is_shared"]:
                                logger.info(f"  - Shared: Yes")
                                logger.info(
                                    f"  - Access type: {sharing_info['access_type']}"
                                )
                                for perm in sharing_info["permissions"]:
                                    logger.info(
                                        f"  - Permission: {perm['email']} ({perm['role']})"
                                    )
                            else:
                                logger.info(f"  - Shared: No")

                        files.append((entry.path_display, entry, metadata_dict))

                if not result.has_more:
                    break

                result = self.dropbox_client.files_list_folder_continue(result.cursor)

            # Filter by exclude patterns
            exclude_patterns = self.config["source"].get("exclude_patterns", [])
            filtered_files = []

            for file_data in files:
                file_path = file_data[0]
                exclude = False
                for pattern in exclude_patterns:
                    if pattern in file_path:
                        exclude = True
                        break

                if not exclude:
                    filtered_files.append(file_data)

            return filtered_files

        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise

    async def migrate(self):
        """
        メイン移行処理を実行

        以下の手順でファイル移行を行います：
        1. 認証の設定（Dropbox・Google Drive）
        2. ファイルリストの取得とメタデータ収集
        3. 共有ドライブの検証（使用する場合）
        4. ファイル単位での移行処理（ダウンロード→アップロード）
        5. 共有設定の適用
        6. エラーハンドリングとリトライ

        テストモードの場合は、設定されたテストフォルダのみを対象とします。
        ドライランモードの場合は、実際のファイル移行は行いません。

        Raises:
            Exception: 認証、ファイル取得、移行処理でエラーが発生した場合
        """
        try:
            # Setup authentication
            self.setup_authentication()

            # Get list of files
            logger.info("Scanning Dropbox files...")
            files = self.list_files_in_folder(self.config["source"]["root_folder"])

            if self.test_mode and len(files) > 10:
                files = files[:10]
                logger.info(f"TEST MODE: Limited to first 10 files")

            logger.info(f"Found {len(files)} files to migrate")

            # Migrate files
            with tqdm(total=len(files), desc="Migrating files") as pbar:
                for file_data in files:
                    file_path = file_data[0]
                    metadata = file_data[1]
                    metadata_dict = file_data[2] if len(file_data) > 2 else {}
                    try:
                        # Download from Dropbox
                        logger.debug(f"Downloading: {file_path}")
                        _, response = self.dropbox_client.files_download(file_path)
                        file_data = response.content

                        # Upload to Google Drive
                        self.upload_file_to_drive(
                            file_path, file_data, metadata, metadata_dict
                        )

                        pbar.update(1)

                        # Small delay to avoid rate limits
                        if not self.dry_run:
                            time.sleep(0.1)

                    except Exception as e:
                        logger.error(f"Failed to migrate {file_path}: {e}")
                        # Simple retry logic
                        retries = self.config["options"].get("max_retries", 3)
                        for attempt in range(1, retries):
                            logger.info(
                                f"Retrying {file_path} (attempt {attempt}/{retries-1})..."
                            )
                            try:
                                time.sleep(self.config["options"].get("retry_delay", 5))
                                _, response = self.dropbox_client.files_download(
                                    file_path
                                )
                                file_data = response.content
                                self.upload_file_to_drive(
                                    file_path, file_data, metadata, metadata_dict
                                )
                                break
                            except Exception as retry_error:
                                logger.error(f"Retry {attempt} failed: {retry_error}")
                                if attempt == retries - 1:
                                    if not self.config["options"].get(
                                        "continue_on_error", True
                                    ):
                                        raise

            logger.info("Migration completed successfully!")

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise


def load_config(config_path: str) -> Dict[str, Any]:
    """
    設定ファイル（JSON）を読み込んで辞書として返す

    Args:
        config_path: 設定ファイルのパス

    Returns:
        Dict[str, Any]: 設定内容の辞書

    Raises:
        FileNotFoundError: 設定ファイルが見つからない場合
        json.JSONDecodeError: JSONの形式が正しくない場合
    """
    config_file = Path(config_path)

    if config_file.exists():
        with open(config_file, "r") as f:
            return json.load(f)
    else:
        # Create default configuration
        default_config = {
            "source": {
                "root_folder": "/",
                "exclude_patterns": [".DS_Store", "*.tmp", "~*", "Thumbs.db"],
            },
            "destination": {"root_folder": "/Dropbox Migration", "create_backup": True},
            "test_folder": "/test",  # Folder for test mode
            "options": {
                "preserve_timestamps": True,
                "migrate_permissions": True,
                "chunk_size_mb": 50,
                "parallel_uploads": 3,
                "max_retries": 3,
                "retry_delay": 5,
                "continue_on_error": True,
            },
        }

        with open(config_file, "w") as f:
            json.dump(default_config, f, indent=2)

        logger.info(f"Created default configuration at {config_path}")
        return default_config


def validate_environment() -> tuple[str, str, str, str]:
    """
    必要な環境変数が設定されているかを検証

    Returns:
        tuple[str, str, str, str]: (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
                                   DROPBOX_APP_KEY, DROPBOX_APP_SECRET)

    Raises:
        SystemExit: 必要な環境変数が設定されていない場合
    """
    required_vars = [
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "DROPBOX_APP_KEY",
        "DROPBOX_APP_SECRET",
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
        logger.error("Please set all required environment variables before running.")
        sys.exit(1)

    return (
        os.getenv("GOOGLE_CLIENT_ID"),
        os.getenv("GOOGLE_CLIENT_SECRET"),
        os.getenv("DROPBOX_APP_KEY"),
        os.getenv("DROPBOX_APP_SECRET"),
    )


def main():
    parser = argparse.ArgumentParser(
        description="Migrate files from Dropbox to Google Drive."
    )
    parser.add_argument(
        "--config", default="config.json", help="Path to configuration file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without actual migration",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--test", action="store_true", help="Test mode - migrate only test folder"
    )

    args = parser.parse_args()

    config = args.config
    dry_run = args.dry_run
    verbose = args.verbose
    test = args.test

    # Set logging level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting Dropbox to Google Drive migration...")

    if test:
        logger.info("🧪 TEST MODE ENABLED - Will only migrate files from test folder")

    if dry_run:
        logger.info("🔍 DRY RUN MODE - No files will be actually migrated")

    # Validate environment
    validate_environment()

    # Load configuration
    config_data = load_config(config)

    # Create migration tool
    migration_tool = MigrationTool(config_data, dry_run=dry_run, test_mode=test)

    try:
        # Run migration
        asyncio.run(migration_tool.migrate())
    except KeyboardInterrupt:
        logger.warning("Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
