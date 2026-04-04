"""
RunPod Serverless Handler for Pony Diffusion V6 XL Image Generation
Text prompt -> Generated image (JPEG, Base64)
"""

import runpod
import json
import urllib.request
import urllib.parse
import os
import sys
import time
import base64
import uuid
import shutil
import traceback
import logging
import websocket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

SERVER_ADDRESS = os.environ.get("SERVER_ADDRESS", "127.0.0.1")
COMFYUI_PORT = "8188"

DEFAULT_NEGATIVE_PROMPT = (
    "score_1, score_2, score_3, lowres, bad anatomy, bad hands, text, error, "
    "missing fingers, extra digit, fewer digits, cropped, worst quality, "
    "low quality, jpeg artifacts, signature, watermark, username, blurry"
)

DEFAULT_QUALITY_TAGS = "score_9, score_8_up, score_7_up"


def to_nearest_multiple_of_8(value, name="value"):
    """Round value to nearest multiple of 8 with validation."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number, got: {value}")
    if value < 64 or value > 2048:
        raise ValueError(f"{name} must be between 64 and 2048, got: {value}")
    return round(value / 8) * 8


def wait_for_comfyui():
    """Wait for ComfyUI HTTP server to be ready."""
    url = f"http://{SERVER_ADDRESS}:{COMFYUI_PORT}/system_stats"
    for attempt in range(180):
        try:
            req = urllib.request.Request(url)
            urllib.request.urlopen(req, timeout=5)
            logger.info(f"ComfyUI ready after {attempt + 1} attempts")
            return True
        except Exception:
            if (attempt + 1) % 30 == 0:
                logger.info(f"Waiting for ComfyUI... ({attempt + 1}/180)")
            time.sleep(1)
    raise RuntimeError("ComfyUI failed to start within 180 seconds")


def connect_websocket():
    """Connect to ComfyUI WebSocket."""
    client_id = str(uuid.uuid4())
    ws_url = f"ws://{SERVER_ADDRESS}:{COMFYUI_PORT}/ws?clientId={client_id}"
    for attempt in range(36):
        try:
            ws = websocket.WebSocket()
            ws.connect(ws_url, timeout=10)
            logger.info(f"WebSocket connected after {attempt + 1} attempts")
            return ws, client_id
        except Exception as e:
            if (attempt + 1) % 6 == 0:
                logger.warning(f"WebSocket retry {attempt + 1}/36: {e}")
            time.sleep(5)
    raise RuntimeError("WebSocket connection failed after 36 attempts (3 minutes)")


def queue_prompt(workflow, client_id):
    """Queue a prompt to ComfyUI."""
    url = f"http://{SERVER_ADDRESS}:{COMFYUI_PORT}/prompt"
    payload = json.dumps({"prompt": workflow, "client_id": client_id}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def get_history(prompt_id):
    """Get execution history from ComfyUI."""
    url = f"http://{SERVER_ADDRESS}:{COMFYUI_PORT}/history/{prompt_id}"
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def get_image(filename, subfolder, folder_type):
    """Get generated image from ComfyUI."""
    params = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": folder_type})
    url = f"http://{SERVER_ADDRESS}:{COMFYUI_PORT}/view?{params}"
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req)
    return resp.read()


def handler(job):
    """RunPod serverless handler."""
    job_id = job.get("id", "unknown")
    input_data = job.get("input", {})

    logger.info(f"Job started: {job_id}")

    try:
        # Validate required inputs
        prompt = input_data.get("prompt", "")
        if not prompt:
            return {"error": "prompt is required"}

        # Prepend quality tags unless disabled
        if input_data.get("no_quality_tags", False):
            full_prompt = prompt
        else:
            full_prompt = f"{DEFAULT_QUALITY_TAGS}, {prompt}"

        negative_prompt = input_data.get("negative_prompt", DEFAULT_NEGATIVE_PROMPT)

        # Parameters with validation
        width = to_nearest_multiple_of_8(input_data.get("width", 1024), "width")
        height = to_nearest_multiple_of_8(input_data.get("height", 1024), "height")

        try:
            steps = int(input_data.get("steps", 25))
            seed = int(input_data.get("seed", 42))
            cfg = float(input_data.get("cfg", 7.0))
            quality = int(input_data.get("quality", 90))
        except (TypeError, ValueError) as e:
            return {"error": f"Invalid parameter type: {e}"}

        if not (1 <= steps <= 100):
            return {"error": f"steps must be between 1 and 100, got: {steps}"}
        if not (1 <= quality <= 100):
            return {"error": f"quality must be between 1 and 100, got: {quality}"}

        logger.info(
            f"Parameters: {width}x{height}, steps={steps}, seed={seed}, cfg={cfg}"
        )

        # Load workflow
        with open("/pony_v6_api.json", "r") as f:
            workflow = json.load(f)

        # Set parameters in workflow
        workflow["3"]["inputs"]["text"] = full_prompt
        workflow["4"]["inputs"]["text"] = negative_prompt
        workflow["5"]["inputs"]["width"] = width
        workflow["5"]["inputs"]["height"] = height
        workflow["6"]["inputs"]["seed"] = seed
        workflow["6"]["inputs"]["steps"] = steps
        workflow["6"]["inputs"]["cfg"] = cfg

        # Connect to ComfyUI
        wait_for_comfyui()
        ws, client_id = connect_websocket()

        try:
            # Queue prompt
            result = queue_prompt(workflow, client_id)
            prompt_id = result.get("prompt_id")
            if not prompt_id:
                return {"error": f"Failed to queue prompt: {result}"}

            logger.info(f"Queued prompt: {prompt_id}")

            # Wait for completion via WebSocket
            while True:
                msg = ws.recv()
                if isinstance(msg, str):
                    data = json.loads(msg)
                    msg_type = data.get("type")
                    if msg_type == "executing":
                        exec_data = data.get("data", {})
                        node = exec_data.get("node")
                        if exec_data.get("prompt_id") == prompt_id:
                            if node is None:
                                logger.info("Execution completed")
                                break
                            else:
                                logger.info(f"Executing node: {node}")
                    elif msg_type == "execution_error":
                        error_data = data.get("data", {})
                        logger.error(f"Execution error: {error_data}")
                        return {"error": f"ComfyUI execution error: {error_data}"}

            # Get output image
            history = get_history(prompt_id)
            if prompt_id not in history:
                return {"error": "No history found for prompt"}

            outputs = history[prompt_id].get("outputs", {})

            # Find SaveImage node output (node 8)
            save_node = outputs.get("8", {})
            images = save_node.get("images", [])
            if not images:
                return {"error": "No images generated"}

            image_info = images[0]
            image_data = get_image(
                image_info["filename"],
                image_info.get("subfolder", ""),
                image_info.get("type", "output")
            )

            # Convert to JPEG with specified quality
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(image_data))
            if img.mode == "RGBA":
                img = img.convert("RGB")

            jpeg_buffer = io.BytesIO()
            img.save(jpeg_buffer, format="JPEG", quality=quality)
            jpeg_data = jpeg_buffer.getvalue()

            # Encode to Base64
            b64_image = base64.b64encode(jpeg_data).decode("utf-8")

            logger.info(f"Job completed: {job_id} (output {len(jpeg_data)} bytes)")
            return {"image": f"data:image/jpeg;base64,{b64_image}"}

        finally:
            ws.close()

    except Exception as e:
        logger.error(f"Job failed: {job_id} - {e}")
        traceback.print_exc()
        return {"error": str(e)}


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
