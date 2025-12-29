# タスク実行プロンプト

@prompt/PLAN.md を参照して、指定されたPR（例: PR2）の実装を進めてください。

## 実装フロー

### 1. ブランチ作成
- `feature/<pr番号>-<簡潔な説明>` の形式でブランチを作成
  - 例: `feature/pr-02-http-client-cache`
- `main` ブランチから分岐すること

### 2. TDD（テスト駆動開発）で実装
- **Red**: まず失敗するテストを書く
- **Green**: テストが通る最小限のコードを実装
- **Refactor**: コードを整理・改善
- ユニットテストは `tests/` に配置
- `pytest-httpx` を使用して API モックを作成

### 3. テストの実行
```bash
# 全テストを実行
pytest

# 特定のテストファイルのみ実行
pytest tests/test_list_municipalities.py

# カバレッジレポート
pytest --cov=mlit_mcp --cov-report=html

# 詳細表示付き
pytest -v
```
- 既存のテストが壊れていないことを確認
- 新機能のテストを追加

### 4. コード品質の確認
```bash
# フォーマットチェック
black --check .

# フォーマット適用
black .

# Lintチェック
flake8 mlit_mcp tests

# 型チェック
mypy mlit_mcp
```

### 5. PLAN.md の更新
- 実装したPRのステータスを `(完了)` に更新
- 実装内容の要約を追記

### 6. コミット & プッシュ
- コミットメッセージ形式: `<type>(<scope>): <description>`
  - type: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`
  - 例: `feat(http): add retry logic with tenacity`
- 適切な粒度でコミットを分割

### 7. Pull Request 作成
```bash
gh pr create --title "PR#<番号>: <タイトル>" --body-file - <<'EOF'
## Summary
- ...

## Tests
- pytest
EOF
```

## チェックリスト

- [ ] ブランチを `main` から作成した
- [ ] テストを先に書いた（TDD）
- [ ] 全てのテストがパスする（`pytest`）
- [ ] フォーマットチェックがパス（`black --check .`）
- [ ] Lintチェックがパス（`flake8 mlit_mcp tests`）
- [ ] 型チェックがパス（`mypy mlit_mcp`）
- [ ] PLAN.md を更新した
- [ ] コミットメッセージが適切
- [ ] PRを作成した

## 注意事項

- 既存のテストを壊さないこと
- 依存関係のあるPRがマージされていることを確認
- Pydantic v2を使用すること（データバリデーション）
- 型ヒントを必ず記述すること
- API キーは `.env` で管理し、テストではモックを使用

## プロジェクト構成

```
real-estate/
├── mlit_mcp/               # MCPサーバーパッケージ
│   ├── __main__.py         # エントリーポイント
│   ├── mcp_server.py       # MCPサーバー本体
│   ├── config.py           # 設定管理
│   ├── http_client.py      # HTTPクライアント＆キャッシュ
│   └── tools/              # MCPツール群
│       ├── list_municipalities.py
│       ├── fetch_transactions.py
│       ├── fetch_transaction_points.py
│       ├── fetch_land_price_points.py
│       ├── fetch_urban_planning_zones.py
│       └── fetch_school_districts.py
├── tests/                  # テストコード
│   ├── test_config.py
│   ├── test_http_client.py
│   └── tools/
├── prompt/                 # 仕様書・計画書
│   ├── PLAN.md
│   ├── SPEC.md
│   └── PROMPT.md
└── .env                    # 環境変数（gitignore対象）
```

## 開発コマンドまとめ

```bash
# 仮想環境作成・有効化
python -m venv .venv
source .venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# テスト実行
pytest

# 品質チェック（一括）
black --check . && flake8 mlit_mcp tests && mypy mlit_mcp

# フォーマット適用してからテスト
black . && pytest
```
