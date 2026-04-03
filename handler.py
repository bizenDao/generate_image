"""
RunPod Serverless Handler for FLUX.1 dev + IP-Adapter Image Generation
Reference image + prompt -> Generated image (JPEG, Base64)
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
import websocket

SERVER_ADDRESS = os.environ.get("SERVER_ADDRESS", "127.0.0.1")
COMFYUI_PORT = "8188"


def process_input(input_data, temp_dir, output_filename, input_type):
    """Process input from path, url, or base64."""
    path_key = f"{input_type}_path"
    url_key = f"{input_type}_url"
    base64_key = f"{input_type}_base64"

    output_path = os.path.join(temp_dir, output_filename)

    if path_key in input_data and input_data[path_key]:
        src_path = input_data[path_key]
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"File not found: {src_path}")
        shutil.copy2(src_path, output_path)
        return output_path

    elif url_key in input_data and input_data[url_key]:
        url = input_data[url_key]
        os.system(f'wget -q -O "{output_path}" "{url}"')
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError(f"Failed to download: {url}")
        return output_path

    elif base64_key in input_data and input_data[base64_key]:
        data = input_data[base64_key]
        if "," in data:
            data = data.split(",", 1)[1]
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(data))
        return output_path

    return None


def wait_for_comfyui():
    """Wait for ComfyUI HTTP server to be ready."""
    url = f"http://{SERVER_ADDRESS}:{COMFYUI_PORT}/system_stats"
    for attempt in range(180):
        try:
            req = urllib.request.Request(url)
            urllib.request.urlopen(req, timeout=5)
            print(f"ComfyUI ready after {attempt + 1} attempts", flush=True)
            return True
        except Exception:
            time.sleep(1)
    raise RuntimeError("ComfyUI failed to start within 180 seconds")


def connect_websocket():
    """Connect to ComfyUI WebSocket."""
    client_id = str(uuid.uuid4())
    ws_url = f"ws://{SERVER_ADDRESS}:{COMFYUI_PORT}/ws?clientId={client_id}"
    for attempt in range(36):
        try:
            ws = websocket.create_connection(ws_url, timeout=10)
            print(f"WebSocket connected after {attempt + 1} attempts", flush=True)
            return ws, client_id
        except Exception:
            time.sleep(5)
    raise RuntimeError("WebSocket connection failed after 36 attempts")


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


def upload_image(filepath, comfyui_filename):
    """Upload image to ComfyUI input directory."""
    import mimetypes
    boundary = uuid.uuid4().hex
    mime_type = mimetypes.guess_type(filepath)[0] or "image/png"

    with open(filepath, "rb") as f:
        file_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{comfyui_filename}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

    url = f"http://{SERVER_ADDRESS}:{COMFYUI_PORT}/upload/image"
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    print(f"Uploaded image: {result}", flush=True)
    return result


def apply_lora_to_workflow(workflow, lora_pairs):
    """Apply LoRA configurations to the workflow.

    Dynamically chains LoraLoaderModelOnly nodes between the IP-Adapter output
    and the sampler input.
    """
    if not lora_pairs:
        return workflow

    max_loras = 4
    lora_pairs = lora_pairs[:max_loras]

    # Find the IP-Adapter output node (node 9) and sampler node (node 11)
    # Chain: IPAdapter(9) -> LoRA1 -> LoRA2 -> ... -> KSampler(11)
    prev_model_output = ["9", 0]  # IP-Adapter output

    for i, lora in enumerate(lora_pairs):
        node_id = str(100 + i)
        lora_name = lora.get("name", "")
        weight = lora.get("weight", 1.0)

        if not lora_name:
            continue

        workflow[node_id] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": prev_model_output,
                "lora_name": lora_name,
                "strength_model": weight,
            }
        }
        prev_model_output = [node_id, 0]

    # Point sampler to the last LoRA output
    workflow["11"]["inputs"]["model"] = prev_model_output

    return workflow


def handler(job):
    """RunPod serverless handler."""
    input_data = job.get("input", {})
    temp_dir = f"/tmp/generate_image_{job['id']}"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Validate required inputs
        prompt = input_data.get("prompt", "")
        if not prompt:
            return {"error": "prompt is required"}

        # Process reference image
        image_path = process_input(input_data, temp_dir, "input_image.png", "image")
        if not image_path:
            return {"error": "Reference image is required (image_path, image_url, or image_base64)"}

        # Parameters
        negative_prompt = input_data.get("negative_prompt", "")
        width = input_data.get("width", 1024)
        height = input_data.get("height", 1024)
        steps = input_data.get("steps", 20)
        seed = input_data.get("seed", 42)
        guidance = input_data.get("guidance", 3.5)
        ip_adapter_weight = input_data.get("ip_adapter_weight", 0.8)
        lora_pairs = input_data.get("lora_pairs", [])
        quality = input_data.get("quality", 90)

        # Round dimensions to nearest multiple of 16
        width = round(width / 16) * 16
        height = round(height / 16) * 16

        print(f"Generating image: {width}x{height}, steps={steps}, seed={seed}, "
              f"guidance={guidance}, ip_weight={ip_adapter_weight}", flush=True)

        # Upload reference image to ComfyUI
        comfyui_image_name = f"ref_{job['id']}.png"
        upload_image(image_path, comfyui_image_name)

        # Load workflow
        with open("/flux_ipadapter_api.json", "r") as f:
            workflow = json.load(f)

        # Set parameters in workflow
        # Node 4: Positive prompt
        workflow["4"]["inputs"]["text"] = prompt
        # Node 5: Negative prompt
        workflow["5"]["inputs"]["text"] = negative_prompt
        # Node 6: Reference image
        workflow["6"]["inputs"]["image"] = comfyui_image_name
        # Node 9: IP-Adapter weight
        workflow["9"]["inputs"]["weight"] = ip_adapter_weight
        # Node 10: Image dimensions
        workflow["10"]["inputs"]["width"] = width
        workflow["10"]["inputs"]["height"] = height
        # Node 11: Sampler settings
        workflow["11"]["inputs"]["seed"] = seed
        workflow["11"]["inputs"]["steps"] = steps
        # Node 14: Guidance scale
        workflow["14"]["inputs"]["value"] = guidance

        # Apply LoRA if specified
        workflow = apply_lora_to_workflow(workflow, lora_pairs)

        # Connect to ComfyUI
        wait_for_comfyui()
        ws, client_id = connect_websocket()

        try:
            # Queue prompt
            result = queue_prompt(workflow, client_id)
            prompt_id = result.get("prompt_id")
            if not prompt_id:
                return {"error": f"Failed to queue prompt: {result}"}

            print(f"Queued prompt: {prompt_id}", flush=True)

            # Wait for completion via WebSocket
            while True:
                msg = ws.recv()
                if isinstance(msg, str):
                    data = json.loads(msg)
                    msg_type = data.get("type")
                    if msg_type == "executing":
                        exec_data = data.get("data", {})
                        if exec_data.get("prompt_id") == prompt_id and exec_data.get("node") is None:
                            print("Execution completed", flush=True)
                            break
                    elif msg_type == "execution_error":
                        error_data = data.get("data", {})
                        return {"error": f"ComfyUI execution error: {error_data}"}

            # Get output image
            history = get_history(prompt_id)
            if prompt_id not in history:
                return {"error": "No history found for prompt"}

            outputs = history[prompt_id].get("outputs", {})

            # Find SaveImage node output (node 13)
            save_node = outputs.get("13", {})
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

            return {"image": f"data:image/jpeg;base64,{b64_image}"}

        finally:
            ws.close()

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
