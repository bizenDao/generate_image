# generate_image

[English](docs/README_en.md)

FLUX.1 dev + IP-Adapter による参照画像ベースの画像生成API（RunPod Serverless）

## 概要

参照画像とテキストプロンプトから新しい画像を生成するAPI。ComfyUIバックエンドでFLUX.1 devモデルとIP-Adapterを組み合わせ、RunPod Serverless上で動作する。

## 機能

- 参照画像からのスタイル/コンテンツ転写（IP-Adapter）
- テキストプロンプトによる生成制御
- LoRAサポート（最大4つ）
- JPEG出力（品質指定可能）
- 入力方式: ファイルパス / URL / Base64

## API パラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `prompt` | string | (必須) | 生成プロンプト |
| `image_path/url/base64` | string | (必須) | 参照画像 |
| `negative_prompt` | string | "" | ネガティブプロンプト |
| `width` | int | 1024 | 画像幅（16の倍数に自動調整） |
| `height` | int | 1024 | 画像高さ（16の倍数に自動調整） |
| `steps` | int | 20 | 推論ステップ数 |
| `seed` | int | 42 | ランダムシード |
| `guidance` | float | 3.5 | ガイダンススケール |
| `ip_adapter_weight` | float | 0.8 | IP-Adapterの影響度 (0.0-1.0) |
| `quality` | int | 90 | JPEG品質 (1-100) |
| `lora_pairs` | array | [] | LoRA設定 |

### LoRA設定

```json
{
  "lora_pairs": [
    {"name": "lora_name.safetensors", "weight": 1.0}
  ]
}
```

LoRAファイルは `/runpod-volume/loras/` または `/ComfyUI/models/loras/` に配置。

## セットアップ

### 1. Docker イメージをビルド

```bash
docker build -t generate-image .
```

### 2. RunPod にデプロイ

RunPod Serverless Endpoint として Docker イメージをデプロイ。

### 3. テスト

```bash
cp .env.example .env
# .env にAPIキーとエンドポイントIDを設定
./test/test_api.sh ./example_image.png "anime girl in a garden" 1024 1024
```

## Python クライアント

```python
from generate_image_client import GenerateImageClient

client = GenerateImageClient("endpoint-id", "api-key")
result = client.create_image(
    image_path="./reference.png",
    prompt="a beautiful landscape painting",
    ip_adapter_weight=0.8,
    guidance=3.5,
)
client.save_image_result(result, "./output.jpg")
```

## 構成

| コンポーネント | 詳細 |
|--------------|------|
| 生成モデル | FLUX.1 dev (fp8量子化) |
| 参照画像処理 | IP-Adapter FLUX |
| テキストエンコーダ | T5-XXL (fp8) + CLIP-L |
| CLIP Vision | SigCLIP ViT-L/14@384 |
| バックエンド | ComfyUI |
| GPU | NVIDIA Ada 24GB |
| 出力形式 | JPEG (Base64) |
