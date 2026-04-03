#!/bin/bash
set -e

echo "Starting ComfyUI server..."
python /ComfyUI/main.py --listen --port 8188 &

echo "Waiting for ComfyUI to be ready..."
MAX_WAIT=120
WAITED=0
until curl -s http://127.0.0.1:8188/system_stats > /dev/null 2>&1; do
    sleep 1
    WAITED=$((WAITED + 1))
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "ERROR: ComfyUI failed to start within ${MAX_WAIT} seconds"
        exit 1
    fi
done
echo "ComfyUI is ready (waited ${WAITED}s)"

echo "Starting RunPod handler..."
exec python /handler.py
