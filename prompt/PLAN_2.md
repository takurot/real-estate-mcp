## MCP サーバー実装計画（PLAN_2）

### 前提

- 実装言語: Python 3.11、`fastapi` + `mcp` SDK。
- HTTP クライアント: `httpx.AsyncClient`、リトライは `tenacity`、キャッシュは `cachetools`＋一時ファイル。
- API キーは `.env` 経由で供給し、テスト時はダミーキー＋ `pytest-httpx` モックを使用。

### PR 一覧（依存と並列性）

| PR                                       | タイトル                                                 | 主目的                                    | 依存    | 並列可 |
| ---------------------------------------- | -------------------------------------------------------- | ----------------------------------------- | ------- | ------ |
| **PR1 (完了 @2025-11-22 GPT-5.1 Codex)** | サーバー雛形と設定基盤                                   | MCP サーバー骨格と設定ローディング        | -       | ×      |
| PR2                                      | HTTP クライアント＆キャッシュ層                          | 共通 HTTP / リトライ / LRU / 一時ファイル | PR1     | ×      |
| PR3                                      | `list_municipalities` ツール                             | 市区町村一覧ツールとスキーマ              | PR2     | ○      |
| PR4                                      | `fetch_transactions` ツール                              | 集計版取引データ取得＋テーブル整形        | PR2     | ○      |
| PR5                                      | `fetch_transaction_points` ツール                        | GeoJSON（取引ポイント）＋ resource 化     | PR2     | ○      |
| PR6                                      | `fetch_land_price_points` & `fetch_urban_planning_zones` | 公示地価・都市計画 GIS 取得               | PR5     | ○      |
| PR7                                      | `fetch_school_districts` & MVT 取扱い                    | 学区タイル＆base64 返却                   | PR5     | ○      |
| PR8                                      | ロギング・監視・キャッシュ運用                           | ヒット率計測、force refresh 実装          | PR2     | ○      |
| PR9                                      | 統合テストとドキュメント                                 | end-to-end / 負荷テスト / README          | PR3–PR8 | ×      |

（○=依存関係を満たした後に他 PR と並列進行可能なタスク）

---

### PR1: サーバー雛形と設定基盤

- **作業**: `fastapi` ベースの MCP サーバープロセスを作成。`list_tools`, `call_tool`, `list_resources`, `read_resource` のハンドラ骨格を実装。`.env` と設定クラス（`pydantic-settings`）を導入し、API キー未設定時に起動失敗させる。
- **テスト**:
  - `tests/test_config.py`: 必須環境変数が無い場合に例外を投げる。
  - `tests/test_server_boot.py`: `TestClient` で基本エンドポイントが 200 を返す。
- **依存**: なし（初期 PR）。
- **並列性**: なし。

### PR2: HTTP クライアント＆キャッシュ層

- **作業**: `httpx.AsyncClient` をシングルトン管理し、`tenacity` の指数バックオフ（429/5xx 対応）を組み込む。JSON レスポンスは TTL 付き LRU（例: 6h/256 entries）に格納し、GeoJSON/MVT はハッシュベースの一時ファイルとして保存。`CacheStore` 抽象化と `force_refresh` フラグを追加。
- **テスト**:
  - `tests/test_http_client.py`: 429→ 成功のリトライ挙動、タイムアウト設定。
  - `tests/test_cache.py`: TTL 失効、force refresh、ファイルキャッシュのクリーンアップ。
- **依存**: PR1。
- **並列性**: なし。

### PR3: `list_municipalities` ツール（並列可）

- **作業**: 入力スキーマ（都道府県コード）と出力スキーマ（コード・名称）を `pydantic` で定義し、MLIT `XIT002` を呼び出すツールを実装。キャッシュ利用とログ出力（HIT/MISS）を組み込む。
- **テスト**:
  - `tests/tools/test_list_municipalities.py`: 正常系（HTTP モック）、引数バリデーション、キャッシュヒット。
- **依存**: PR2。
- **並列性**: ○（PR4/PR5 と並行可能）。

### PR4: `fetch_transactions` ツール（並列可）

- **作業**: `XIT001` に対する入力（年度範囲、分類コード、都市コード）検証とレスポンス整形。`format` 引数で `json` / `table`（行列形式）を選択できるようにし、`pandas` 互換構造を JSON 化。
- **テスト**:
  - `tests/tools/test_fetch_transactions.py`: 正常系、年度逆転時のバリデーションエラー、`table` 形式変換。
- **依存**: PR2。
- **並列性**: ○（PR3/PR5 と並行可能）。

### PR5: `fetch_transaction_points` ツール（並列可）

- **作業**: GeoJSON を取得する `XIT003` ツールを実装。レスポンスサイズが 1MB 超の場合は一時ファイル化し、MCP `resource://` を返す。`bbox` フィルター（任意）をサポート。
- **テスト**:
  - `tests/tools/test_fetch_transaction_points.py`: GeoJSON 直接返却と resource 返却の両ケース、bbox 未指定時の動作。
- **依存**: PR2。
- **並列性**: ○（PR3/PR4 と並行可能）。

### PR6: `fetch_land_price_points` & `fetch_urban_planning_zones`（並列可）

- **作業**: `XKT001`（地価公示）と `XKT011`（都市計画区域）のツールを追加。`response_format`=`geojson`/`pbf` を切り替え可能にし、MVT は base64 で返却。共通の GIS 変換ヘルパを用意。
- **テスト**:
  - `tests/tools/test_fetch_land_price_points.py`: `geojson` / `pbf` の双方をモックしデコード可否を確認。
  - `tests/tools/test_fetch_urban_planning_zones.py`: `z/x/y` vs `bbox` のバリデーション。
- **依存**: PR5（resource 取り扱いロジックを流用）。
- **並列性**: ○（PR7, PR8 と並行可能）。

### PR7: `fetch_school_districts` & MVT 取扱い（並列可）

- **作業**: `XKT021`（小学校区）のツールを実装し、MVT を base64 で返却する共通ハンドラを整備。`pyproj` で座標系変換（必要に応じ CRS 指定）をサポート。大容量レスポンスは resource 化。
- **テスト**:
  - `tests/tools/test_fetch_school_districts.py`: MVT base64 返却、CRS 無効指定時のエラー。
- **依存**: PR5（resource 処理）。
- **並列性**: ○（PR6, PR8 と並行可能）。

### PR8: ロギング・監視・キャッシュ運用（並列可）

- **作業**: リクエストごとにツール名/所要時間/キャッシュヒット率を構造化ログで出力。5 分毎にキャッシュ統計を出すバックグラウンドタスクを追加。`force_refresh` パラメーターを各ツールに露出し、README に記載。
- **テスト**:
  - `tests/test_logging.py`: キャッシュヒット時にログへ `cache=hit` が出力される。
  - `tests/test_force_refresh.py`: `force_refresh=True` で HTTP が再実行される。
- **依存**: PR2（キャッシュ層完成後）。
- **並列性**: ○（PR6, PR7 と並行可能）。

### PR9: 統合テストとドキュメント

- **作業**: `tests/test_integration.py` で MCP `call_tool` → HTTP モック → resource 応答までの E2E を実装。`pytest-benchmark` を用いた 50 req/min の擬似負荷テストを追加。README にセットアップ手順、ツール一覧、制限、キャッシュ方針、テスト手順を記載。
- **テスト**:
  - `tests/test_integration.py`: 代表 3 ツールで end-to-end。
  - `tests/test_rate_limit.py`: 429 を返すモックでバックオフが働くか確認。
  - `pytest --maxfail=1 --disable-warnings -q` を CI 想定で実行。
- **依存**: PR3〜PR8 完了後。
- **並列性**: なし（最終統合作業）。

---

### 依存関係メモ

- PR1 → PR2 → {PR3, PR4, PR5, PR8} → {PR6, PR7} → PR9。
- PR3 / PR4 / PR5 は PR2 完了後に並列実装可能。
- PR6 と PR7 は PR5（Geo resource）の実装完了が前提だが、互いは並列可能。
- PR8 はキャッシュ層完成後であれば PR6/PR7 と並行可。
- 統合テスト/ドキュメント（PR9）は最後に集約。
