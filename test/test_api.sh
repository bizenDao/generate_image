#!/bin/bash
# Test script for FLUX.1 + IP-Adapter Image Generation API
#
# Usage:
#   ./test/test_api.sh [image_path] [prompt] [width] [height]
#
# Example:
#   ./test/test_api.sh ./example_image.png "anime girl in a garden" 1024 1024

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env"
fi

if [ -z "$RUNPOD_API_KEY" ] || [ -z "$RUNPOD_ENDPOINT_ID" ]; then
    echo "ERROR: RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID must be set"
    echo "Copy .env.example to .env and fill in your credentials"
    exit 1
fi

IMAGE_PATH="${1:-$PROJECT_DIR/example_image.png}"
PROMPT="${2:-a beautiful anime girl, detailed, high quality}"
WIDTH="${3:-1024}"
HEIGHT="${4:-1024}"

if [ ! -f "$IMAGE_PATH" ]; then
    echo "ERROR: Image not found: $IMAGE_PATH"
    exit 1
fi

echo "=== FLUX.1 + IP-Adapter Image Generation Test ==="
echo "Image: $IMAGE_PATH"
echo "Prompt: $PROMPT"
echo "Size: ${WIDTH}x${HEIGHT}"

# Encode image to base64
IMAGE_BASE64=$(base64 < "$IMAGE_PATH")

# Build request JSON
REQUEST_JSON=$(cat <<EOF
{
  "input": {
    "prompt": "$PROMPT",
    "image_base64": "$IMAGE_BASE64",
    "width": $WIDTH,
    "height": $HEIGHT,
    "steps": 20,
    "seed": 42,
    "guidance": 3.5,
    "ip_adapter_weight": 0.8,
    "quality": 90
  }
}
EOF
)

# Submit job
echo ""
echo "Submitting job..."
RESPONSE=$(curl -s -X POST \
    "https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/run" \
    -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "$REQUEST_JSON")

JOB_ID=$(echo "$RESPONSE" | jq -r '.id')

if [ "$JOB_ID" = "null" ] || [ -z "$JOB_ID" ]; then
    echo "ERROR: Failed to submit job"
    echo "$RESPONSE" | jq .
    exit 1
fi

echo "Job ID: $JOB_ID"

# Poll for completion
echo "Waiting for completion..."
ELAPSED=0
MAX_WAIT=300

while [ $ELAPSED -lt $MAX_WAIT ]; do
    STATUS_RESPONSE=$(curl -s \
        "https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/status/${JOB_ID}" \
        -H "Authorization: Bearer ${RUNPOD_API_KEY}")

    STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')

    if [ "$STATUS" = "COMPLETED" ]; then
        echo "Completed! (${ELAPSED}s)"

        # Save output image
        OUTPUT_DIR="$SCRIPT_DIR/output"
        mkdir -p "$OUTPUT_DIR"
        OUTPUT_FILE="$OUTPUT_DIR/output_$(date +%Y%m%d_%H%M%S).jpg"

        echo "$STATUS_RESPONSE" | jq -r '.output.image' | sed 's/data:image\/jpeg;base64,//' | base64 -d > "$OUTPUT_FILE"
        echo "Saved: $OUTPUT_FILE"
        exit 0
    elif [ "$STATUS" = "FAILED" ]; then
        echo "FAILED!"
        echo "$STATUS_RESPONSE" | jq .
        exit 1
    else
        echo "  Status: $STATUS (${ELAPSED}s)"
        sleep 10
        ELAPSED=$((ELAPSED + 10))
    fi
done

echo "ERROR: Timed out after ${MAX_WAIT}s"
exit 1
