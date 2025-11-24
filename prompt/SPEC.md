## MLIT 不動産情報ライブラリ MCP サーバー仕様

### 1. 背景と目的
- 国土交通省「不動産情報ライブラリ」の公開 API 群（取引価格、地価公示、防災・都市計画・周辺施設など 30+ 種別）を MCP（Model Context Protocol）経由で利用できるようにする。  
- API は HTTPS で JSON/GeoJSON/ベクトルタイルを返却し、サブスクリプションキーをヘッダーに付与する必要がある。[MLIT API 操作説明](https://www.reinfolib.mlit.go.jp/help/apiManual/)
- 既存の分析・可視化タスク（例: `evalGrowthRate.py`）から統一インタフェースでデータを取得し、将来的な自動化や LLM エージェント連携を容易にする。

### 2. 想定利用者
- アプリ/ツール開発者: 価格や地価、公示ポイントを取得して独自の分析を実施。
- 研究者/データサイエンティスト: 国土数値情報（駅乗降客数、災害危険区域等）を解析。
- LLM/MCP クライアント: プロンプトから自然文でデータ取得を指示。

### 3. システム全体構成
| レイヤ | 役割 | 選定 |
| --- | --- | --- |
| Transport | MCP Server over stdio/WebSocket | 既存 MCP SDK (TS or Python) |
| Business | エンドポイント定義・バリデーション・レスポンス整形 | Custom |
| Data Access | MLIT API 呼び出し | `requests` / `fetch` + retry |
| Config | サービス設定 | `.env` or MCP config JSON |
| Observability | Structured logging + metrics | `pino`/`structlog` 等 |

### 4. 依存関係と環境変数
- `MLIT_API_BASE=https://www.reinfolib.mlit.go.jp/ex-api/external`
- `MLIT_API_KEY`（サブスクリプションキー。HTTP ヘッダー `Ocp-Apim-Subscription-Key` に設定）
- Optional: `MLIT_DEFAULT_FORMAT=json`（`json` | `geojson` | `pbf`）
- 推奨ライブラリ:
  - TypeScript: `node>=20`, `@modelcontextprotocol/sdk`, `zod`, `node-fetch@3`, `pino`.
  - Python: `python>=3.11`, `mcp`, `httpx`, `pydantic`.

### 5. MCP サーバーが提供するツール
| Tool 名 | 用途 | バックエンド API | 主要パラメータ | 返却 |
| --- | --- | --- | --- | --- |
| `mlit.getTransactions` | 取引価格/成約価格一覧 | API #1 | `pref_code`, `city_code`, `term` | JSON list |
| `mlit.listMunicipalities` | 都道府県内市区町村一覧 | API #2 | `pref_code` | JSON list |
| `mlit.getAppraisalDocs` | 鑑定評価書情報 | API #3 | `pref_code`, `year` | JSON |
| `mlit.getTransactionPoints` | 取引ポイント (GeoJSON) | API #4 | `bbox` or `mesh_code` | GeoJSON |
| `mlit.getLandPricePoints` | 地価公示・調査ポイント | API #5 | 同上 | GeoJSON |
| `mlit.getUrbanPlanLayer` | 都市計画系レイヤ（区域/用途/立地適正化/防火/地区計画/高度利用/都市計画道路） | API #6,7,8,9,10,11,19,28,29,32 | `layer_type`, `zxy` or `bbox` | GeoJSON / PBF |
| `mlit.getNationalSpatialData` | 国土数値情報（学校/医療/福祉/駅/災害等） | API #12–27, 30–31 | `dataset`, `filters`, `format` | JSON/GeoJSON/PBF |

#### Tool 設計指針
1. **引数バリデーション**: `pref_code` は 2 桁、`city_code` は 5 桁、`mesh_code` は 8/10/11 桁に制限。`bbox` は `[minLon, minLat, maxLon, maxLat]`。
2. **`format` 自動判定**: 明示されない場合はポイント系は `geojson`、テーブル系は `json`。
3. **ページング**: 取引価格 API は `page`, `limit` パラメータを MCP 側で提供し、レスポンスに `next_page` を含める。
4. **キャッシュ**: メモリ LRU (key=method+params) + 任意でディスク (`.cache/mlit/{hash}.json`)。TTL は 1 時間、Geo レイヤは 24 時間。
5. **レート制御**: デフォルト 1 req/sec、`p-retry` 等で指数バックオフ（`maxRetry=3`, `baseDelay=1.0`）。

### 6. リクエスト生成規約
1. ベース URL: `${MLIT_API_BASE}/{DATASET_ID}`。DATASET_ID は MLIT ドキュメント掲載 ID（例: `XKT025`）。
2. 共通クエリ:
   - `response_format`: `json` / `geojson` / `pbf`
   - `lang`: `ja` or `en`（対応エンドポイントのみ。#1, #2）
   - `z`,`x`,`y`: XYZ タイル要求時必須。
3. 認証: ヘッダー `Ocp-Apim-Subscription-Key: ${MLIT_API_KEY}`（マニュアル記載の「サブスクリプションキー」）。
4. Geo フィルタ:
   - `distance` / `lat` / `lon`（ポイント検索）
   - `mesh_code`（国土数値メッシュ）
   - `bbox` をサーバー側で `minx,miny,maxx,maxy` クエリに変換。
5. 取引系フィルタ:
   - `term`: `YYYY-YYYY`
   - `usage`: `residential|commercial|other`
   - `structure`, `area_from/to`, `price_from/to`

### 7. レスポンス整形
- MCP レスポンスは `data` と `meta` を分離。
- `data`: MLIT からの JSON/GeoJSON をそのまま返し、ポイント系は `FeatureCollection` を保証。`pbf` 取得時は base64 エンコード。
- `meta`:
  - `source`: `reinfolib.mlit.go.jp`
  - `dataset`: `transaction`, `urban_plan`, etc.
  - `request_id`, `fetched_at`, `cache_hit`.
- エラー時は `error.code`, `error.message`, `error.status`, `upstream_id` を返却。

### 8. エラーハンドリング
| ケース | 対応 |
| --- | --- |
| 4xx (400/403/404) | パラメータ再確認案内 + 原文メッセージ。API キー不備は `ConfigError`。 |
| 429 | Retry-After を尊重しバックオフ。上限超過をユーザに通知。 |
| 5xx | 3 回リトライ後に `UpstreamFailure`。 |
| タイムアウト | `timeout=30s`、再試行後にアボート。 |
| フォーマット不一致 | スキーマ検証エラーを `ValidationError` として提示。 |

### 9. ロギング・メトリクス
- `level=info`: tool 呼び出し、エンドポイント、キャッシュ状況、所要時間。
- `level=debug`: 実際の URL（クエリのみ、キーはマスク）。
- メトリクス: `requests_total{tool,status}`, `latency_ms`, `cache_hit_ratio`.

### 10. テスト戦略
1. **Unit**: パラメータバリデーション、URL/クエリ生成、キャッシュロジック。
2. **Integration (offline)**: `nock`/`responses` で API レスポンスをモックし、ツールの JSON を固定化。
3. **Integration (online, optional)**: API キーを保持する開発者のみ実行。`pytest -m "mlit_live"` / `npm run test:live`。
4. **Contract**: スキーマ（GeoJSON FeatureCollection）を JSON Schema で検証。

### 11. セキュリティ & ガバナンス
- API キーはクライアントに露出させない（MCP サーバー内でのみ保持）。
- ログではキーを `****` マスク。  
- 通信経路は HTTPS のみ。  
- 取得データの出典明記: `データ出典: 国土交通省 不動産情報ライブラリ`。  
- 利用規約に従い再配布・商用利用の制約を README / ドキュメントに記載。

### 12. 導入手順（ドラフト）
1. API 利用申請を実施しキー取得（MLIT サイトの案内に従う）。  
2. `.env` に `MLIT_API_KEY=...` を設定。  
3. `npm install` または `pip install -r requirements.txt`。  
4. `npm run dev` / `python mcp_server.py` でサーバー起動。  
5. MCP 対応クライアント (Cursor, Claude Desktop 等) にサーバー設定を登録。

### 13. 今後の拡張候補
- レスポンス正規化（共通の地物属性スキーマ）。
- ローカルタイルキャッシュ (MBTiles)。
- バルクダウンロードジョブとバッチ処理 API。
- 追加データソース（国交省 G 空間情報センター）とのフェデレーション。

---
この仕様は MLIT 公開 API 操作説明書の要件に基づき、MCP サーバーとして実装する際の最低限の契約・設計情報をまとめたものである。[MLIT API 操作説明](https://www.reinfolib.mlit.go.jp/help/apiManual/)

