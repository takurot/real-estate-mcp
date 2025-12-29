# MLIT Real Estate MCP Server

日本の国土交通省「不動産情報ライブラリ」API を利用し、不動産取引価格・地価公示・都市計画などの情報を LLM (Large Language Model) エージェントに提供する MCP (Model Context Protocol) サーバーです。

## 特徴

- **MCP 対応**: Cursor, Claude Desktop などの MCP クライアントから直接利用可能。
- **キャッシュ機能**: API レスポンスをキャッシュし、API 制限や待機時間を緩和。
- **GeoJSON/MVT 対応**: 大規模な地理データは MCP の `resource://` として効率的に受け渡し。
- **堅牢性**: レート制限 (429) やサーバーエラーに対する自動リトライ。

## 必要なもの

- Python 3.11 以上
- **国土交通省 API キー**
  - [不動産情報ライブラリ API 利用申請](https://www.reinfolib.mlit.go.jp/ex-api/external/XIT001) から取得してください。

## インストール

1. リポジトリをクローン:
   ```bash
   git clone https://github.com/takurot/real-estate-heatmap.git
   cd real-estate-heatmap
   ```

2. 依存パッケージのインストール:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. 環境変数の設定:
   `.env` ファイルを作成し、API キーを設定します。
   ```bash
   MLIT_API_KEY=your_api_key_here
   ```

## 使い方 (MCP サーバーとして実行)

### 1. Cursor / Claude Desktop での設定

MCP クライアントの設定ファイル (例: `claude_desktop_config.json` や Cursor の MCP 設定) に以下を追加します。

```json
{
  "mcpServers": {
    "mlit": {
      "command": "/path/to/real-estate-heatmap/.venv/bin/python",
      "args": ["-m", "mlit_mcp"],
      "env": {
        "MLIT_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

### 2. コマンドラインでの動作確認

サーバーは標準入出力 (stdio) を使用するため、手動で実行しても何も表示されずに待機状態になります。
開発用デバッグには MCP Inspector 等を利用するか、ログファイルを確認してください。

## 利用可能なツール

| ツール名 | 説明 |
| --- | --- |
| `mlit.list_municipalities` | 指定した都道府県の市区町村コード一覧を取得 |
| `mlit.fetch_transactions` | 不動産取引価格情報の検索・取得 (期間・場所指定) |
| `mlit.fetch_transaction_points` | 取引情報のポイントデータを GeoJSON で取得 |
| `mlit.fetch_land_price_points` | 地価公示・地価調査ポイントの取得 |
| `mlit.fetch_urban_planning_zones` | 都市計画区域・用途地域などの取得 |

## 開発者向け

### テスト実行
```bash
pytest
```

### 実装計画
詳細は [prompt/PLAN.md](prompt/PLAN.md) を参照してください。

---
**Note**: 本リポジトリは以前の「不動産価格成長率分析ツール」から MCP サーバーへ移行しました。旧分析スクリプトのロジックは今後 MCP クライアントとして再実装される予定です。
