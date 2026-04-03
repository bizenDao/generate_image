# デプロイ・テストガイド

## 前提条件

- Docker がインストール済み
- DockerHub アカウント (`bizenyakiko`)
- RunPod アカウント + API キー
- HuggingFace アクセス（FLUX.1 dev のダウンロードに必要）

## 1. Docker イメージのビルド

```bash
cd /Users/goodsun/develop/bizeny/generate_image

# ビルド（モデルダウンロードを含むため30分〜1時間程度）
docker build -t bizenyakiko/generate-image:latest .
```

### ビルド時の注意

- FLUX.1 dev fp8: 約12GB
- T5-XXL fp8 + CLIP-L: 約5GB
- VAE (ae.safetensors): 約300MB
- CLIP Vision + IP-Adapter: 約2GB
- 合計: 約20GBのモデルダウンロード
- 十分なディスク空き容量（50GB以上推奨）とネットワーク帯域を確保すること

### HuggingFace認証が必要な場合

```bash
# FLUX.1 dev はゲート付きモデルの場合がある
docker build --build-arg HF_TOKEN=hf_xxxxx -t bizenyakiko/generate-image:latest .
```

## 2. DockerHub へプッシュ

```bash
docker login
docker push bizenyakiko/generate-image:latest
```

## 3. RunPod Serverless Endpoint の作成

### RunPod Console での設定

1. https://www.runpod.io/console/serverless にアクセス
2. **New Endpoint** をクリック
3. 以下を設定:

| 設定項目 | 値 |
|---------|-----|
| Endpoint Name | `generate-image` |
| Container Image | `bizenyakiko/generate-image:latest` |
| Container Disk | 80 GB |
| GPU | Ada Lovelace 24GB (RTX 4090 等) |
| GPU Count | 1 |
| Max Workers | 1（必要に応じて増加） |
| Idle Timeout | 5s（コスト優先）/ 300s（レスポンス優先） |
| CUDA Version | 12.8 |

4. **Deploy** をクリック

### Endpoint ID の取得

デプロイ後、ダッシュボードに表示される Endpoint ID をメモ。

## 4. 環境変数の設定

```bash
cp .env.example .env
```

`.env` を編集:

```
RUNPOD_API_KEY=your-actual-api-key
RUNPOD_ENDPOINT_ID=your-actual-endpoint-id
```

## 5. テスト実行

### シェルスクリプトでテスト

```bash
# テスト画像を用意（example_image.png）
./test/test_api.sh ./example_image.png "a beautiful anime girl" 1024 1024
```

出力は `test/output/output_YYYYMMDD_HHMMSS.jpg` に保存される。

### Python クライアントでテスト

```bash
pip install requests python-dotenv

python generate_image_client.py
```

### curl で直接テスト

```bash
source .env

# 画像をBase64エンコード
IMAGE_B64=$(base64 < example_image.png)

# ジョブ送信
JOB_ID=$(curl -s -X POST \
  "https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/run" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"input\":{\"prompt\":\"a beautiful anime girl\",\"image_base64\":\"${IMAGE_B64}\"}}" \
  | jq -r '.id')

echo "Job ID: $JOB_ID"

# ステータス確認
curl -s \
  "https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/status/${JOB_ID}" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" | jq .status
```

## 6. トラブルシューティング

### ビルドが失敗する

| エラー | 原因 | 対処 |
|--------|------|------|
| HuggingFace 403 | ゲート付きモデル | HF_TOKEN を設定、モデルページで利用規約に同意 |
| Disk space | ディスク不足 | `docker system prune` で空き確保 |
| Network timeout | ダウンロード失敗 | 再実行、またはミラーを使用 |

### ジョブが FAILED になる

| エラーメッセージ | 原因 | 対処 |
|-----------------|------|------|
| ComfyUI failed to start | コンテナ起動失敗 | RunPod ログを確認、ディスク容量を増加 |
| No images generated | ワークフロー実行失敗 | プロンプトやパラメータを確認 |
| OOM (Out of Memory) | VRAM不足 | 解像度を下げる (768x768)、ステップ数を減らす |

### コールドスタートが遅い

- Idle Timeout を増やす（ウォームスタート維持）
- Min Workers を 1 にする（常時稼働、コスト増）

## 7. LoRA の追加

RunPod Network Volume を使用:

1. RunPod Console → **Network Volumes** → 新規作成
2. LoRA ファイルを `/runpod-volume/loras/` にアップロード
3. Endpoint 設定で Network Volume を紐づけ
4. API 呼び出し時に `lora_pairs` パラメータで指定

```json
{
  "lora_pairs": [
    {"name": "my_style.safetensors", "weight": 0.8}
  ]
}
```
