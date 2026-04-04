# generate_image

[English](docs/README_en.md)

Pony Diffusion V6 XL によるアニメ/キャラクター画像生成API（RunPod Serverless）

## 概要

テキストプロンプトからアニメ・イラスト・キャラクター画像を生成するAPI。ComfyUIバックエンドでPony Diffusion V6 XLモデルを使用し、RunPod Serverless上で動作する。

## 機能

- テキストからアニメ/キャラクター画像生成
- 自動品質タグ付与（score_9, score_8_up, score_7_up）
- JPEG出力（品質指定可能）
- 軽量モデル（6.5GB）で高速生成

## API パラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `prompt` | string | (必須) | 生成プロンプト |
| `negative_prompt` | string | (auto) | ネガティブプロンプト |
| `width` | int | 1024 | 画像幅（8の倍数に自動調整） |
| `height` | int | 1024 | 画像高さ（8の倍数に自動調整） |
| `steps` | int | 25 | 推論ステップ数 |
| `seed` | int | 42 | ランダムシード |
| `cfg` | float | 7.0 | CFGスケール |
| `quality` | int | 90 | JPEG品質 (1-100) |
| `no_quality_tags` | bool | false | 品質タグ自動付与を無効化 |

## 使用例

```json
{
  "input": {
    "prompt": "1girl, blue hair, cherry blossoms, garden, detailed illustration"
  }
}
```

## セットアップ

### 1. Docker イメージをビルド

```bash
docker build -t generate-image .
```

### 2. RunPod にデプロイ

RunPod Serverless Endpoint として Docker イメージをデプロイ。

## 構成

| コンポーネント | 詳細 |
|--------------|------|
| 生成モデル | Pony Diffusion V6 XL (SDXL, 6.5GB) |
| CLIP Skip | 2 |
| サンプラー | Euler Ancestral |
| バックエンド | ComfyUI |
| GPU | NVIDIA 8GB+ |
| 出力形式 | JPEG (Base64) |
