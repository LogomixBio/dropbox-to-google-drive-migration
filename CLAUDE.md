# Dropbox to Google Drive Migration Tool

## 概要
DropboxからGoogle Drive（共有ドライブ対応）へデータを効率的に移行するワンタイムマイグレーションツール。ファイル構造とメタデータを保ちつつ、共有設定を詳細に表示・移行することを目的とする。

## 主要機能

### 1. **ファイル・フォルダ構造の完全保持**

- Dropbox内のディレクトリ構造をGoogle Driveに完全に再現
- ファイル名、フォルダ名の維持
- タイムスタンプ（更新日時）のRFC 3339フォーマットでの保持
- パス正規化による重複フォルダ作成の防止

### 2. **Google Workspace共有ドライブ対応**

- 共有ドライブの自動検出と検証
- 共有ドライブへの直接移行（中間フォルダなし）
- 共有ドライブアクセス権限の事前確認

### 3. **共有設定の詳細表示と移行**

- Dropboxの共有情報を詳細に表示（アクセスタイプ、権限一覧）
- Google Driveの権限システムへの自動マッピング
- 共有設定移行の可視化とログ記録

### 4. **認証トークンの自動管理**

- Dropbox・Google Drive両方の認証トークンを自動保存
- 次回実行時の自動ログイン
- 不正なトークンの自動削除と再認証

### 5. **堅牢なエラーハンドリング**

- 自動リトライ機能（設定可能な回数・間隔）
- 詳細なエラーログとファイル別の処理状況
- エラー時の継続実行オプション

## 技術スタック
- **実行環境**: ローカル Python環境（Docker非使用）
- **言語**: Python 3.8+
- **認証**:
  - Dropbox: OAuth 2.0 with Scoped Access
  - Google Drive: OAuth 2.0 with Drive API
- **主要ライブラリ**:
  - dropbox: Dropbox公式SDK v11+
  - google-api-python-client: Google Drive API v2
  - google-auth-oauthlib: OAuth認証
  - tqdm: リアルタイム進捗表示
  - argparse: コマンドライン引数処理

## アーキテクチャ

### 実際のファイル構成

```text
dropbox-to-google-drive-migration/
├── CLAUDE.md                  # 仕様書（このファイル）
├── README.md                  # ユーザー向けドキュメント
├── Makefile                   # ビルド・実行コマンド
├── requirements.txt           # Python依存関係
├── config.json                # 設定ファイル
├── main.py                    # 統合エントリーポイント（全機能実装）
├── .gitignore                 # Git除外設定（トークンファイル含む）
├── dropbox_token.pickle       # Dropbox認証トークン（Git除外）
└── token.pickle               # Google Drive認証トークン（Git除外）
```

### クラス設計（main.py内）
```python
class MigrationTool:
    """統合移行ツールクラス"""

    # 認証関連
    def authenticate_dropbox() -> dropbox.Dropbox
    def authenticate_google_drive() -> googleapiclient.discovery.Resource
    def setup_authentication()

    # Google Drive操作
    def get_shared_drive_id(drive_name: str) -> Optional[str]
    def create_folder_in_drive(folder_name: str, parent_id: Optional[str]) -> str
    def ensure_folder_structure(dropbox_path: str) -> str

    # ファイル処理
    def upload_file_to_drive(file_path: str, file_data: bytes,
                           dropbox_metadata: FileMetadata,
                           metadata_dict: Dict[str, Any])
    def get_file_sharing_info(file_id: str) -> Dict[str, Any]
    def apply_sharing_permissions(file_id: str, sharing_info: Dict[str, Any])

    # メイン処理
    def list_files_in_folder(folder_path: str = "") -> List[tuple]
    async def migrate()
```

## 処理フロー

### 1. **初期化フェーズ**
- 環境変数の検証（API キー・シークレット）
- 認証トークンの確認（存在すれば再利用、無効なら再認証）
- APIクライアントの初期化と疎通確認
- 設定ファイル（config.json）の読み込み

### 2. **スキャンフェーズ**
- テストモード時: `/test`フォルダまたはルートから最大10ファイル
- 通常モード時: 指定されたルートフォルダから再帰的スキャン
- 各ファイルの詳細メタデータ収集:
  - ファイルサイズ、更新日時、ファイルID
  - 共有設定（アクセスタイプ、権限一覧）
- 除外パターンによるフィルタリング

### 3. **移行フェーズ**
- 共有ドライブの検証と選択
- フォルダ構造の事前作成（重複チェック付き）
- ファイル単位での処理:
  1. Dropboxからのダウンロード
  2. MIMEタイプの自動検出
  3. RFC 3339形式でのタイムスタンプ変換
  4. Google Driveへのアップロード（チャンク対応）
  5. 共有権限の適用
- リアルタイム進捗表示とエラーハンドリング

### 4. **完了・ログ出力**
- 移行完了の確認とサマリー表示
- 詳細ログの保存（logs/migration.log）
- エラーファイルの一覧化

## 共有設定のマッピング

### Dropbox → Google Drive権限変換
| Dropbox権限/ロール | Google Drive権限 | 実装ロジック |
|------------------|-----------------|------------|
| 'edit' を含む権限 | writer | 編集権限を付与 |
| 'view' を含む権限 | reader | 閲覧権限を付与 |
| 'comment' を含む権限 | commenter | コメント権限を付与 |
| その他/不明 | reader | デフォルトで閲覧権限 |

### 共有情報の詳細表示

```text
Found file: /test/README.md
  - Size: 6,778 bytes
  - Modified: 2025-06-15T14:21:07
  - File ID: id:mAqoc0jUai8AAAAAAAAAFw
  - Shared: Yes
  - Access type: AccessLevel('owner', None)
  - Permission: user@example.com (editor)
```

## 実行方法

### 前提条件
- Python 3.8以上
- Google Cloud ProjectでのGoogle Drive API有効化
- Dropbox APIアプリの登録と必要スコープの有効化:
  - `files.metadata.read`
  - `files.content.read`
  - `sharing.read`
  - `account_info.read`

### コマンド実行例

```bash
# ヘルプ表示
make help

# セットアップ
make setup

# テストモード（/testフォルダのみ）
make test

# 本格移行
make run

# ドライラン（実際の移行なし）
make dry-run

# 詳細ログ付きで実行
make verbose

# 詳細ログ付きテストモード
make test-verbose
```

## 設定オプション（config.json）

### 現在の設定ファイル構造
```json
{
  "source": {
    "root_folder": "/",
    "exclude_patterns": [".DS_Store", "*.tmp", "~*", "Thumbs.db"]
  },
  "destination": {
    "root_folder": "",                           // 空=""で共有ドライブルートに直接
    "create_backup": true,
    "use_shared_drive": true,
    "shared_drive_name": "01_Logomix_migration-test"
  },
  "test_folder": "/test",                        // テストモード対象フォルダ
  "options": {
    "preserve_timestamps": true,                 // タイムスタンプ保持
    "migrate_permissions": true,                 // 共有設定移行
    "chunk_size_mb": 50,
    "parallel_uploads": 3,
    "max_retries": 3,
    "retry_delay": 5,
    "continue_on_error": true
  }
}
```

## セキュリティ実装

### 認証トークン管理
- **保存場所**: ローカルファイル（`*.pickle`）
- **Git除外**: `.gitignore`で除外設定済み
- **自動検証**: 起動時にトークンの有効性を確認
- **自動更新**: 無効なトークンは自動削除して再認証

### API権限の最小化
- **Dropbox**: 読み取り専用スコープのみ
- **Google Drive**: ファイル作成・共有権限のみ
- **暗号化**: 全通信をHTTPS経由で実行

## エラーハンドリング実装

### 自動リトライ
- **対象**: ネットワークエラー、レート制限、一時的な API エラー
- **設定**: `max_retries`（デフォルト3回）、`retry_delay`（デフォルト5秒）
- **戦略**: 指数バックオフなし（固定間隔）

### ログ記録
- **詳細ログ**: `logs/migration.log`
- **エラーファイル**: 処理失敗ファイルの一覧化
- **継続実行**: `continue_on_error`でエラー時も継続可能

## 制限事項と既知の問題

### 重複ファイル処理
- **現状**: 重複チェックなし（同名ファイルが複数作成される可能性）
- **回避策**: 初回実行前に移行先を空にする、テストモードでの事前確認

### 共有設定移行の制約
- **制限**: Google Workspace管理者権限が必要（共有ドライブ使用時）
- **注意**: Dropboxの複雑な権限は簡略化される場合がある

### パフォーマンス
- **同期処理**: 現在は非同期処理未実装（逐次アップロード）
- **大容量**: 5GB以上のファイルは分割処理が推奨

## 今後の拡張可能性

- 重複ファイルの検出と上書き確認機能
- 真の非同期並列アップロード
- 差分同期（増分移行）機能
- Web UI での進捗可視化
- Google Workspace Enterprise機能への対応
