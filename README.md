# Dropbox to Google Drive Migration Tool

## 🎯 このツールは何ができるの？

このツールは、**Dropboxに保存しているファイルをGoogle Driveに引っ越しする**ためのプログラムです。

例えば：
- 📁 Dropboxの容量がいっぱいになってきた
- 💰 Dropboxの有料プランを解約してGoogle Driveに移行したい
- 🏢 会社でGoogle Workspaceを使うことになった
- 🔄 バックアップとしてGoogle Driveにもファイルを保存したい

こんな時に、**ボタン一つで全てのファイルを自動で移動**できます！

## ✨ 主な特徴

### 1. **フォルダ構造をそのまま維持** 📂
Dropboxでキレイに整理したフォルダ構造を、Google Driveでも完全に再現します。
```
Dropbox:                    Google Drive:
📁 仕事                  →  📁 仕事
  📁 2024年プロジェクト  →    📁 2024年プロジェクト
    📄 企画書.pdf       →      📄 企画書.pdf
```

### 2. **共有設定も引き継ぎ** 👥
他の人と共有しているファイルの設定も、可能な限りGoogle Driveに引き継ぎます。

### 3. **大きなファイルも安心** 📦
動画や大容量ファイルも、自動的に分割してアップロードするので失敗しません。

### 4. **進捗が見える** 📊
どのファイルを処理中か、あと何ファイル残っているかが一目で分かります。

### 5. **失敗しても大丈夫** 🔄
途中でエラーが起きても、自動的にリトライします。また、中断したところから再開もできます。

## 📋 必要なもの

1. **Docker Desktop**（推奨）または Python 3.11以上
2. **Dropboxアカウント**と**Googleアカウント**（同じメールアドレスがベスト）
3. 少し時間（API設定に約15分）

## 🛠 セットアップ手順（初心者向け）

### ステップ1: Dropbox APIの設定（5分）

1. [Dropbox開発者ページ](https://www.dropbox.com/developers/apps)にアクセス
2. 「Create app」ボタンをクリック
3. 以下を選択：
   - 「Choose an API」→「Scoped access」を選択
   - 「Choose the type of access」→「Full Dropbox」を選択
   - アプリ名を入力（例：「My Migration Tool」）
4. 作成後、表示される**App key**と**App secret**をメモ 📝

### ステップ2: Google Drive APIの設定（10分）

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 「プロジェクトを作成」をクリック（名前は何でもOK）
3. 左メニューから「APIとサービス」→「ライブラリ」
4. 「Google Drive API」を検索して「有効にする」をクリック
5. 「認証情報」→「認証情報を作成」→「OAuth クライアント ID」
6. アプリケーションの種類：「デスクトップアプリ」を選択
7. 表示される**クライアントID**と**クライアントシークレット**をメモ 📝

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

### 最も簡単な方法（Docker使用）

```bash
make start
```

これだけ！自動的に全てのファイルが移行されます。

### その他の実行方法

#### お試し実行（実際には移行しない）
```bash
python src/main.py --dry-run
```

#### 詳細な進捗を見たい場合
```bash
python src/main.py --verbose
```

#### 途中で止まった場合の再開
```bash
python src/main.py --resume
```

## ⚙️ カスタマイズ（オプション）

`config.json`ファイルで細かい設定ができます：

```json
{
  "source": {
    "root_folder": "/",                          // Dropboxの移行元フォルダ
    "exclude_patterns": [".DS_Store", "*.tmp"]   // 移行しないファイル
  },
  "destination": {
    "root_folder": "/Dropbox Migration",         // Google Driveの保存先
    "create_backup": true                        // バックアップを作成
  },
  "options": {
    "parallel_uploads": 3                        // 同時アップロード数（速度調整）
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

### Q: 途中で止めても大丈夫？
A: はい！`Ctrl+C`で安全に停止でき、`--resume`オプションで続きから再開できます。

### Q: 無料で使える？
A: はい！ただし、Google DriveとDropboxの容量制限は各サービスの契約に依存します。

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

### その他のエラー
`logs/migration.log`ファイルを確認してください。詳細なエラー情報が記録されています。

## 📝 注意事項

- 🔒 **セキュリティ**: APIキーは他人に教えないでください
- 💾 **容量**: 移行先のGoogle Driveに十分な空き容量があることを確認
- 🌐 **ネットワーク**: 安定したインターネット接続が必要です
- ⏰ **時間**: 大量のファイルがある場合は、夜間や週末の実行がおすすめ
