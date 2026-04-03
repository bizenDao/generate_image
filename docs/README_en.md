# generate_image

Image generation API using FLUX.1 dev + IP-Adapter on RunPod Serverless.

## Overview

Generate new images from reference images and text prompts. Combines FLUX.1 dev model with IP-Adapter on a ComfyUI backend, deployed on RunPod Serverless.

## Features

- Style/content transfer from reference images (IP-Adapter)
- Text prompt-based generation control
- LoRA support (up to 4)
- JPEG output with configurable quality
- Input methods: file path / URL / Base64

## API Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | string | (required) | Generation prompt |
| `image_path/url/base64` | string | (required) | Reference image |
| `negative_prompt` | string | (auto) | Negative prompt (sensible default provided) |
| `width` | int | 1024 | Image width (auto-rounded to nearest 16) |
| `height` | int | 1024 | Image height (auto-rounded to nearest 16) |
| `steps` | int | 20 | Inference steps (1-100) |
| `seed` | int | 42 | Random seed |
| `guidance` | float | 3.5 | Guidance scale |
| `ip_adapter_weight` | float | 0.8 | IP-Adapter influence (0.0-2.0) |
| `quality` | int | 90 | JPEG quality (1-100) |
| `lora_pairs` | array | [] | LoRA configurations |

### LoRA Configuration

```json
{
  "lora_pairs": [
    {"name": "lora_name.safetensors", "weight": 1.0}
  ]
}
```

Place LoRA files in `/runpod-volume/loras/` or `/ComfyUI/models/loras/`.

## Setup

### 1. Build Docker Image

```bash
docker build -t generate-image .
```

### 2. Deploy to RunPod

Deploy the Docker image as a RunPod Serverless Endpoint.

### 3. Test

```bash
cp .env.example .env
# Set your API key and endpoint ID in .env
./test/test_api.sh ./example_image.png "anime girl in a garden" 1024 1024
```

## Python Client

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

### With LoRA

```python
result = client.create_image(
    image_path="./reference.png",
    prompt="a beautiful landscape painting",
    lora_pairs=[{"name": "style_lora.safetensors", "weight": 0.8}],
)
```

## Architecture

| Component | Details |
|-----------|---------|
| Generation Model | FLUX.1 dev (fp8 quantized) |
| Reference Image | IP-Adapter FLUX |
| Text Encoders | T5-XXL (fp8) + CLIP-L |
| CLIP Vision | SigCLIP ViT-L/14@384 |
| Backend | ComfyUI |
| GPU | NVIDIA Ada 24GB |
| Output | JPEG (Base64) |
