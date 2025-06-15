.PHONY: help setup run test dry-run verbose clean

# デフォルトターゲット（ヘルプ表示）
all: help

help:
	@echo "Dropbox to Google Drive Migration Tool"
	@echo "DropboxからGoogle Driveへの移行ツール"
	@echo ""
	@echo "使用方法："
	@echo "  make setup     - Python依存関係をインストール"
	@echo "  make test      - テストモード（/testフォルダのみ移行）"
	@echo "  make run       - 本格移行を実行"
	@echo "  make dry-run   - ドライラン（実際の移行なし）"
	@echo "  make verbose   - 詳細ログ付きで実行"
	@echo "  make clean     - 一時ファイルを削除"
	@echo ""
	@echo "環境変数の設定も忘れずに："
	@echo "  export GOOGLE_CLIENT_ID=\"your-client-id\""
	@echo "  export GOOGLE_CLIENT_SECRET=\"your-client-secret\""
	@echo "  export DROPBOX_APP_KEY=\"your-app-key\""
	@echo "  export DROPBOX_APP_SECRET=\"your-app-secret\""

# 依存関係のインストール
setup:
	pip install -r requirements.txt
	@echo ""
	@echo "✅ セットアップ完了！環境変数を設定してから 'make test' でテストしてください"

# テストモード（/testフォルダのみ）
test:
	python main.py --test

# 本格移行
run:
	python main.py

# ドライラン（実際の移行なし）
dry-run:
	python main.py --dry-run

# 詳細ログ付きで実行
verbose:
	python main.py --verbose

# 詳細ログ付きテストモード
test-verbose:
	python main.py --test --verbose

# 一時ファイルの削除
clean:
	rm -f token.pickle dropbox_token.pickle
	rm -rf __pycache__ logs/
	find . -name "*.pyc" -delete
	@echo "✅ 一時ファイルを削除しました"