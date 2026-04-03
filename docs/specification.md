# API 仕様書

## エンドポイント

### ジョブ送信

```
POST https://api.runpod.ai/v2/{ENDPOINT_ID}/run
```

### ステータス確認

```
GET https://api.runpod.ai/v2/{ENDPOINT_ID}/status/{JOB_ID}
```

### 同期実行（短時間ジョブ向け）

```
POST https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync
```

## 認証

```
Authorization: Bearer {RUNPOD_API_KEY}
```

## リクエスト

### リクエストボディ

```json
{
  "input": {
    "prompt": "string (required)",
    "image_path": "string (optional)",
    "image_url": "string (optional)",
    "image_base64": "string (optional)",
    "negative_prompt": "string (optional)",
    "width": 1024,
    "height": 1024,
    "steps": 20,
    "seed": 42,
    "guidance": 3.5,
    "ip_adapter_weight": 0.8,
    "quality": 90,
    "lora_pairs": []
  }
}
```

### パラメータ詳細

#### prompt (必須)

生成する画像の説明テキスト。英語推奨。

```
"a beautiful anime girl in a garden, detailed illustration, soft lighting"
```

#### 参照画像 (必須: いずれか1つ)

| パラメータ | 形式 | 説明 |
|-----------|------|------|
| `image_path` | string | サーバーローカルのファイルパス |
| `image_url` | string | HTTP/HTTPS URL（120秒タイムアウト） |
| `image_base64` | string | Base64エンコード文字列（data URI可） |

- `image_base64` は `data:image/png;base64,iVBOR...` 形式も受け付ける
- 複数指定時は `image_path` > `image_url` > `image_base64` の優先順

#### negative_prompt

除外したい要素の指定。未指定時はデフォルト値が使用される。

デフォルト値:
```
lowres, bad anatomy, bad hands, text, error, missing fingers,
extra digit, fewer digits, cropped, worst quality, low quality,
normal quality, jpeg artifacts, signature, watermark, username,
blurry, deformed, ugly, duplicate, morbid, mutilated
```

#### width / height

| 制約 | 値 |
|------|-----|
| 最小値 | 64 |
| 最大値 | 4096 |
| 倍数制約 | 16の倍数に自動丸め |
| デフォルト | 1024 |

推奨解像度:

| アスペクト比 | 解像度 |
|-------------|--------|
| 1:1 | 1024 x 1024 |
| 3:4 (ポートレート) | 768 x 1024 |
| 4:3 (ランドスケープ) | 1024 x 768 |
| 9:16 (縦長) | 576 x 1024 |
| 16:9 (横長) | 1024 x 576 |

#### steps

推論ステップ数。多いほど高品質だが生成時間が増加。

| 値 | 範囲 | 推奨 |
|----|------|------|
| デフォルト | 20 | 通常用途 |
| 最小 | 1 | テスト用 |
| 最大 | 100 | 最高品質 |
| 推奨範囲 | 15-30 | 品質/速度バランス |

#### seed

乱数シード。同じseed + 同じパラメータで再現可能な結果を得られる。

| 値 | 説明 |
|----|------|
| 42 (デフォルト) | 固定シード |
| -1 | ランダム（毎回異なる結果） |
| 任意の整数 | 再現用 |

#### guidance

FLUX.1のガイダンススケール。プロンプトへの忠実度を制御。

| 値 | 効果 |
|----|------|
| 1.0 | 低い忠実度、創造的 |
| 3.5 (デフォルト) | バランス |
| 7.0 | 高い忠実度、プロンプトに忠実 |

#### ip_adapter_weight

参照画像の影響度。

| 値 | 効果 |
|----|------|
| 0.0 | 参照画像の影響なし |
| 0.5 | 軽い参照 |
| 0.8 (デフォルト) | 強い参照 |
| 1.0 | 最大影響 |
| 1.0-2.0 | 過剰（スタイル強制、品質低下の可能性） |

#### quality

JPEG出力品質。

| 値 | ファイルサイズ | 画質 |
|----|-------------|------|
| 70 | 小 | やや劣化 |
| 85 | 中 | 良好 |
| 90 (デフォルト) | やや大 | 高品質 |
| 95 | 大 | 最高品質 |
| 100 | 最大 | 無劣化 |

#### lora_pairs

LoRA (Low-Rank Adaptation) モデルの適用設定。最大4つまで。

```json
{
  "lora_pairs": [
    {
      "name": "style_lora.safetensors",
      "weight": 1.0
    },
    {
      "name": "character_lora.safetensors",
      "weight": 0.7
    }
  ]
}
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `name` | string | LoRAファイル名 (.safetensors) |
| `weight` | float | 適用強度 (デフォルト: 1.0) |

LoRAはモデルに対してチェーン適用される:
```
FLUX.1 → IP-Adapter → LoRA1 → LoRA2 → ... → Sampler
```

## レスポンス

### 送信レスポンス

```json
{
  "id": "job-uuid-here",
  "status": "IN_QUEUE"
}
```

### ステータスレスポンス

#### 成功

```json
{
  "id": "job-uuid-here",
  "status": "COMPLETED",
  "output": {
    "image": "data:image/jpeg;base64,/9j/4AAQ..."
  }
}
```

#### 処理中

```json
{
  "id": "job-uuid-here",
  "status": "IN_PROGRESS"
}
```

#### 失敗

```json
{
  "id": "job-uuid-here",
  "status": "FAILED",
  "output": {
    "error": "error description"
  }
}
```

### ステータス一覧

| ステータス | 説明 |
|-----------|------|
| `IN_QUEUE` | キューで待機中 |
| `IN_PROGRESS` | 生成処理中 |
| `COMPLETED` | 完了（output にデータあり） |
| `FAILED` | 失敗（output.error に詳細） |
| `CANCELLED` | キャンセル済み |

## エラーレスポンス

| エラー | 原因 |
|--------|------|
| `prompt is required` | prompt パラメータ未指定 |
| `Reference image is required` | 参照画像未指定 |
| `Base64 decode failed` | 不正なBase64データ |
| `width must be between 64 and 4096` | 解像度が範囲外 |
| `steps must be between 1 and 100` | ステップ数が範囲外 |
| `Download timed out after 120s` | URL画像のダウンロードタイムアウト |
| `ComfyUI execution error` | ワークフロー実行エラー |
| `No images generated` | 画像生成失敗 |

## 処理フロー

```
1. クライアント → RunPod API: ジョブ送信
2. RunPod → コンテナ: handler.py 呼び出し
3. handler.py:
   a. 入力バリデーション
   b. 参照画像の取得 (path/url/base64)
   c. ComfyUI へ画像アップロード
   d. ワークフロー JSON にパラメータ設定
   e. LoRA ノードの動的追加（指定時）
   f. ComfyUI WebSocket 接続
   g. プロンプトキューイング
   h. 実行完了待ち
   i. 出力画像取得
   j. JPEG変換 + Base64エンコード
4. RunPod → クライアント: レスポンス返却
```

## パフォーマンス目安

| 条件 | 所要時間 (目安) |
|------|---------------|
| 1024x1024, 20 steps, ADA_24 | 10-20秒 |
| 768x1024, 20 steps, ADA_24 | 8-15秒 |
| 1024x1024, 30 steps, ADA_24 | 15-30秒 |
| コールドスタート追加 | +30-60秒 |

※ LoRA適用時は追加で数秒増加。
