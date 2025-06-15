# Dropbox to Google Drive Migration Tool

## 🎯 このツールは何ができるの？

このツールは、**DropboxからGoogle Drive（共有ドライブ対応）に効率的にデータ移行**を行うためのPythonアプリケーションです。

例えば：
- 📁 Dropboxから Google Workspace の共有ドライブへの移行
- 💰 組織のクラウドストレージ戦略の変更
- 🏢 チームデータの集約・統合
- 🔄 データのバックアップと冗長化

**ワンコマンドで全てのファイルを自動移行**し、フォルダ構造と共有設定を保持します！

## ✨ 主な特徴

### 1. **フォルダ構造をそのまま維持** 📂
Dropboxでキレイに整理したフォルダ構造を、Google Driveでも完全に再現します。
```
Dropbox:                    Google Drive:
📁 仕事                  →  📁 仕事
  📁 2024年プロジェクト  →    📁 2024年プロジェクト
    📄 企画書.pdf       →      📄 企画書.pdf
```

### 2. **Google Workspace共有ドライブ対応** 🏢
共有ドライブへの直接移行をサポート。チーム全体でのデータ共有が簡単です。

### 3. **共有設定の詳細表示と移行** 👥
Dropboxの共有情報を詳細に表示し、Google Driveの権限にマッピングして移行します。

### 4. **メタデータ保持** 📅
ファイルの更新日時、サイズなどの重要な情報をそのまま保持します。

### 5. **進捗の可視化** 📊
リアルタイムでファイル処理状況、共有設定、エラー詳細を表示します。

### 6. **堅牢なエラーハンドリング** 🔄
自動リトライ機能と詳細なログ記録で、大規模移行も安心です。

### 7. **認証トークンの自動保存** 🔐
一度認証すれば、次回以降は自動的にログインできます。

## 📋 必要なもの

1. **Python 3.8以上**
2. **Dropboxアカウント**と**Googleアカウント**（同じメールアドレスがベスト）
3. 少し時間（API設定に約15分）

## 🛠 セットアップ手順（初心者向け）

### ステップ1: Dropbox APIの設定（5分）

1. [Dropbox開発者ページ](https://www.dropbox.com/developers/apps)にアクセス
2. 「Create app」ボタンをクリック
3. 以下を選択：
   - 「Choose an API」→「Scoped access」を選択
   - 「Choose the type of access」→「Full Dropbox」を選択
   - アプリ名を入力（例：「Migration Tool」）
4. **重要**: 「Permissions」タブで以下のスコープを有効化：
   - `files.metadata.read`
   - `files.content.read`
   - `sharing.read`
   - `account_info.read`
5. 「Settings」タブで**App key**と**App secret**をメモ 📝

### ステップ2: Google Drive APIの設定（10分）

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 「プロジェクトを作成」をクリック（名前は何でもOK）
3. 左メニューから「APIとサービス」→「ライブラリ」
4. 「Google Drive API」を検索して「有効にする」をクリック
5. **重要**: 共有ドライブを使用する場合は、Google Workspace管理者権限が必要
6. 「認証情報」→「認証情報を作成」→「OAuth クライアント ID」
7. アプリケーションの種類：「デスクトップアプリ」を選択
8. 表示される**クライアントID**と**クライアントシークレット**をメモ 📝

### ステップ3: ツールの準備

1. このツールをダウンロード
2. ターミナル（Mac）またはコマンドプロンプト（Windows）を開く
3. ダウンロードしたフォルダに移動

### ステップ4: 認証情報の設定

メモした4つの情報を設定します。以下のコマンドをターミナルで実行（実際の値に置き換えて）：

```bash
export GOOGLE_CLIENT_ID="ここにGoogleのクライアントIDを貼り付け"
export GOOGLE_CLIENT_SECRET="ここにGoogleのシークレットを貼り付け"
export DROPBOX_APP_KEY="ここにDropboxのApp keyを貼り付け"
export DROPBOX_APP_SECRET="ここにDropboxのApp secretを貼り付け"
```

💡 **ヒント**: Windowsの場合は`export`の代わりに`set`を使います

## 🚀 実行方法

### 最初のセットアップ（必須）

```bash
# 1. Pythonライブラリをインストール
make setup

# 2. 環境変数を設定（上記のステップ4を参照）
export GOOGLE_CLIENT_ID="..."
# など
```

### 実行方法

#### 通常の実行
```bash
make run
# または
python main.py
```

#### テストモード（限定フォルダのみ移行）
```bash
make test
# または
python main.py --test
```

**テストモードの詳細仕様：**

1. **対象フォルダ**: `config.json`の`test_folder`設定（デフォルト: `/test`）
2. **フォルダが存在する場合**: 指定フォルダ内の全ファイルを移行
3. **フォルダが存在しない場合**: ルートフォルダから最大10ファイルまでを移行
4. **用途**:
   - 初回実行前の動作確認
   - 設定やAPIキーの検証
   - 小規模なサンプル移行

**設定例:**
```json
{
  "test_folder": "/sample_data",  // カスタムテストフォルダ
  ...
}
```

#### お試し実行（実際には移行しない）
```bash
python main.py --dry-run
```

#### 詳細な進捗とメタデータを見たい場合
```bash
python main.py --verbose
```

### 🔍 実行時に表示される情報

#### テストモード実行例：

```bash
$ python main.py --test
2025-06-15 23:40:06,113 - __main__ - INFO - 🧪 TEST MODE ENABLED - Will only migrate files from test folder
2025-06-15 23:40:06,113 - __main__ - INFO - Setting up authentication...
2025-06-15 23:40:06,784 - __main__ - INFO - Using saved Dropbox token
2025-06-15 23:40:07,709 - __main__ - INFO - TEST MODE: Checking for test folder /test
2025-06-15 23:40:07,992 - __main__ - INFO - TEST MODE: Found test folder, processing files in /test
2025-06-15 23:40:08,259 - __main__ - INFO - Found file: /test/README.md
2025-06-15 23:40:08,259 - __main__ - INFO -   - Size: 6,778 bytes
2025-06-15 23:40:08,259 - __main__ - INFO -   - Modified: 2025-06-15T14:21:07
2025-06-15 23:40:08,259 - __main__ - INFO -   - File ID: id:mAqoc0jUai8AAAAAAAAAFw
2025-06-15 23:40:08,783 - __main__ - INFO -   - Shared: Yes
2025-06-15 23:40:08,783 - __main__ - INFO -   - Access type: AccessLevel('owner', None)
2025-06-15 23:40:10,682 - __main__ - INFO - Found and verified shared drive: 01_Logomix_migration-test
2025-06-15 23:40:13,351 - __main__ - INFO - Successfully uploaded: /test/README.md (Google Drive ID: 1ABC...xyz)
2025-06-15 23:40:13,351 - __main__ - INFO - Migration completed successfully!
```

#### 通常移行時の表示：

```
Found file: /documents/important.pdf
  - Size: 2,456,789 bytes
  - Modified: 2025-06-14T09:30:15
  - File ID: id:xyz123ABC
  - Shared: No
Successfully uploaded: /documents/important.pdf (Google Drive ID: 1DEF...abc)
Migrating files: 15%|████▌                     | 45/300 [02:30<14:20, 3.37it/s]
```

## ⚙️ カスタマイズ（オプション）

`config.json`ファイルで細かい設定ができます：

```json
{
  "source": {
    "root_folder": "/",                          // Dropboxの移行元フォルダ
    "exclude_patterns": [".DS_Store", "*.tmp", "~*", "Thumbs.db"]
  },
  "destination": {
    "root_folder": "",                           // 空=""で共有ドライブのルートに直接コピー
    "create_backup": true,
    "use_shared_drive": true,                    // 共有ドライブを使用
    "shared_drive_name": "01_Logomix_migration-test"  // 共有ドライブ名
  },
  "test_folder": "/test",                        // テストモード時のフォルダ
  "options": {
    "preserve_timestamps": true,                 // タイムスタンプを保持
    "migrate_permissions": true,                 // 共有設定を移行
    "chunk_size_mb": 50,                        // チャンクサイズ
    "parallel_uploads": 3,                      // 同時アップロード数
    "max_retries": 3,                           // 最大リトライ回数
    "retry_delay": 5,                           // リトライ間隔（秒）
    "continue_on_error": true                   // エラー時も継続
  }
}
```

## ❓ よくある質問

### Q: 移行にどれくらい時間がかかる？
A: ファイルサイズによりますが、目安は以下の通りです：
- 1GB: 約10-20分
- 10GB: 約1-2時間
- 100GB: 約10-20時間

### Q: 元のDropboxファイルは削除される？
A: **いいえ！** このツールはコピーのみ行います。Dropboxのファイルはそのまま残ります。

### Q: 共有ドライブに移行できる？
A: はい！Google Workspaceの共有ドライブに対応しており、チーム全体でのデータ移行が可能です。

### Q: 共有設定は引き継がれる？
A: Dropboxの共有情報を詳細に表示し、Google Driveの権限システムに適切にマッピングして移行します。

### Q: 認証は毎回必要？
A: いいえ！初回認証後はトークンが保存され、次回以降は自動的にログインします。

### Q: 途中で止めても大丈夫？
A: はい！`Ctrl+C`で安全に停止できます。認証トークンは保存されるので、再実行時は認証不要です。

### Q: コピー済みのファイルはどうなる？上書きされる？
A: **現在の実装では重複チェックは行っていません**。同じファイルを再実行すると、Google Drive上に同名のファイルが複数作成される可能性があります。重複を避けたい場合は：
1. 初回実行前に移行先フォルダを空にする
2. テストモード（`--test`）で事前確認する
3. 部分的な移行の場合は、設定ファイルで除外パターンを活用する

## 🆘 困ったときは

### 「環境変数が設定されていません」エラー
```bash
# 再度、環境変数を設定してください
export GOOGLE_CLIENT_ID="your-id-here"
# ...（他の3つも同様）
```

### 「容量が足りません」エラー
1. Google Driveの空き容量を確認
2. 不要なファイルを削除するか、プランをアップグレード

### 「認証に失敗しました」エラー
1. APIが有効になっているか確認
2. App keyやClient IDが正しくコピーされているか確認

### 「共有ドライブが見つかりません」エラー

1. Google Workspace管理者権限があることを確認
2. `config.json`の`shared_drive_name`が正確であることを確認
3. 共有ドライブへのアクセス権限があることを確認

### その他のエラー

`logs/migration.log`ファイルを確認してください。詳細なエラー情報が記録されています。

## 🔐 セキュリティとプライバシー

- **認証トークン**: `*.pickle`ファイルはローカルに保存され、gitリポジトリには含まれません
- **APIキー**: 環境変数で管理し、コードには含めません
- **権限**: 必要最小限のスコープのみを要求します
- **データ**: 全てHTTPS暗号化通信で転送されます

## 📝 注意事項

- 🔒 **セキュリティ**: APIキーとトークンファイルは他人と共有しないでください
- 🏢 **権限**: 共有ドライブを使用する場合はGoogle Workspace管理者権限が必要
- 💾 **容量**: 移行先のGoogle Driveに十分な空き容量があることを確認
- 🌐 **ネットワーク**: 安定したインターネット接続が必要です
- ⏰ **時間**: 大量のファイルがある場合は、夜間や週末の実行がおすすめ
- 👥 **チーム**: 組織での利用時は、必要な権限とポリシーを事前に確認してください
