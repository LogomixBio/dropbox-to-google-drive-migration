# Dropbox to Google Drive Migration Tool

## 概要
DropboxからGoogle Driveへデータを移行するワンタイムマイグレーションツール。ファイル構造を保ちつつ、共有設定を可能な限り引き継ぐことを目的とする。

## 主要機能
1. **ファイル・フォルダ構造の完全保持**
   - Dropbox内のディレクトリ構造をGoogle Driveに完全に再現
   - ファイル名、フォルダ名を維持
   - タイムスタンプ（作成日時、更新日時）の保持

2. **共有設定の移行**
   - Dropboxの共有設定をGoogle Driveの共有設定にマッピング
   - 共有リンクの生成と管理
   - アクセス権限の移行（閲覧のみ、編集可能など）

3. **認証の統一**
   - DropboxとGoogle DriveでGoogle OAuth認証を使用
   - 同一ユーザーアカウントでの移行を想定

## 技術スタック
- **実行環境**: Docker Container
- **言語**: Python 3.11+
- **認証**: Google OAuth 2.0
- **主要ライブラリ**:
  - dropbox: Dropbox公式SDK
  - google-api-python-client: Google Drive API
  - google-auth-oauthlib: OAuth認証
  - tqdm: 進捗表示
  - asyncio: 非同期処理

## アーキテクチャ

### コンポーネント構成
```
dropbox-to-google-drive-migration/
├── CLAUDE.md               # 仕様書（このファイル）
├── Makefile               # ビルド・実行コマンド
├── Dockerfile             # Dockerコンテナ定義
├── docker-compose.yml     # Docker Compose設定
├── requirements.txt       # Python依存関係
├── config.json           # 設定ファイル（自動生成）
├── src/
│   ├── main.py           # エントリーポイント
│   ├── core/
│   │   ├── __init__.py
│   │   ├── migration_engine.py    # 移行処理のコア
│   │   ├── file_mapper.py         # ファイル構造マッピング
│   │   └── permission_mapper.py   # 権限マッピング
│   ├── dropbox_integration/
│   │   ├── __init__.py
│   │   ├── client.py             # Dropbox API クライアント
│   │   └── models.py             # Dropboxデータモデル
│   ├── google_drive_integration/
│   │   ├── __init__.py
│   │   ├── client.py             # Google Drive API クライアント
│   │   └── models.py             # Google Driveデータモデル
│   └── auth/
│       ├── __init__.py
│       └── oauth_manager.py      # OAuth認証管理
└── tests/
    ├── __init__.py
    └── test_migration.py         # テストファイル
```

### 処理フロー
1. **初期化フェーズ**
   - Google OAuth認証（Dropbox・Google Drive共通）
   - APIクライアントの初期化
   - 移行設定の読み込み

2. **スキャンフェーズ**
   - Dropboxのファイル・フォルダ構造を再帰的にスキャン
   - メタデータ（サイズ、更新日時、共有設定）の収集
   - 移行計画の作成

3. **移行フェーズ**
   - ファイルのダウンロード（Dropbox）
   - ファイルのアップロード（Google Drive）
   - フォルダ構造の再現
   - 共有設定の適用

4. **検証フェーズ**
   - ファイル数・サイズの確認
   - 共有設定の確認
   - エラーレポートの生成

## 共有設定のマッピング

### Dropbox → Google Drive
| Dropbox権限 | Google Drive権限 | 備考 |
|------------|-----------------|------|
| Can view | Viewer | 閲覧のみ |
| Can comment | Commenter | コメント可能 |
| Can edit | Editor | 編集可能 |
| Owner | Owner | 所有権（制限あり） |

### 制限事項
- Dropboxの「有効期限付きリンク」は、Google Driveでは手動設定が必要
- チーム共有フォルダは、共有ドライブへの手動移行が推奨
- 大容量ファイル（5GB以上）は分割アップロードが必要

## 実行方法

### 前提条件
- Docker および Docker Compose
- Python 3.11以上（ローカル実行の場合）
- Google Cloud ProjectでのAPI有効化
  - Google Drive API
  - Dropbox APIアプリの登録

### セットアップ
```bash
# 依存関係のインストール
make setup

# 環境変数の設定
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export DROPBOX_APP_KEY="your-app-key"
export DROPBOX_APP_SECRET="your-app-secret"
```

### 実行
```bash
# マイグレーションの実行
make start
```

## 設定オプション

### config.json（自動生成）
```json
{
  "source": {
    "root_folder": "/",
    "exclude_patterns": [".DS_Store", "*.tmp"]
  },
  "destination": {
    "root_folder": "/Dropbox Migration",
    "create_backup": true
  },
  "options": {
    "preserve_timestamps": true,
    "migrate_permissions": true,
    "chunk_size_mb": 50,
    "parallel_uploads": 3
  }
}
```

## エラーハンドリング
- **認証エラー**: トークンのリフレッシュを自動実行
- **レート制限**: 指数バックオフで自動リトライ
- **ネットワークエラー**: 再開可能なアップロード
- **容量不足**: 事前チェックとアラート

## 大容量ファイルの扱い
- 100MB以下: 通常転送
- 100MB-5GB: チャンクアップロード
- 5GB以上: ローカル実行モードへの切り替えを推奨

## セキュリティ考慮事項
- OAuth トークンはキーチェーンに保存
- 転送中のファイルは暗号化（HTTPS）
- 一時ファイルは処理後に確実に削除
- 機密ファイルの検出とアラート機能

## 今後の拡張可能性
- 差分同期機能
- スケジュール実行
- 複数アカウント対応
- 転送進捗のWeb UI