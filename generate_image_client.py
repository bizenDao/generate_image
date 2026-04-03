"""
Python client for FLUX.1 + IP-Adapter Image Generation API on RunPod.

Usage:
    client = GenerateImageClient("endpoint-id", "api-key")
    result = client.create_image(
        image_path="./reference.png",
        prompt="a beautiful landscape painting"
    )
    client.save_image_result(result, "./output.jpg")
"""

import base64
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class GenerateImageClient:
    def __init__(self, runpod_endpoint_id: str, runpod_api_key: str):
        self.endpoint_id = runpod_endpoint_id
        self.base_url = f"https://api.runpod.ai/v2/{self.endpoint_id}"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {runpod_api_key}",
            "Content-Type": "application/json",
        })

    def encode_file_to_base64(self, file_path: str) -> str:
        """Encode a file to Base64 string."""
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def submit_job(self, input_data: Dict[str, Any]) -> str:
        """Submit a job to RunPod API. Returns job ID."""
        resp = self.session.post(
            f"{self.base_url}/run",
            json={"input": input_data},
        )
        resp.raise_for_status()
        result = resp.json()
        job_id = result.get("id")
        if not job_id:
            raise RuntimeError(f"Failed to submit job: {result}")
        logger.info(f"Job submitted: {job_id}")
        return job_id

    def wait_for_completion(
        self,
        job_id: str,
        check_interval: int = 5,
        max_wait_time: int = 300,
    ) -> Dict[str, Any]:
        """Poll job status until completion. Returns result dict."""
        start = time.time()
        while time.time() - start < max_wait_time:
            resp = self.session.get(f"{self.base_url}/status/{job_id}")
            resp.raise_for_status()
            result = resp.json()
            status = result.get("status")

            if status == "COMPLETED":
                logger.info(f"Job completed: {job_id}")
                return result
            elif status == "FAILED":
                error = result.get("error", "Unknown error")
                raise RuntimeError(f"Job failed: {error}")
            elif status in ("IN_QUEUE", "IN_PROGRESS"):
                elapsed = int(time.time() - start)
                logger.info(f"Status: {status} ({elapsed}s elapsed)")
                time.sleep(check_interval)
            else:
                logger.warning(f"Unknown status: {status}")
                time.sleep(check_interval)

        raise TimeoutError(f"Job {job_id} timed out after {max_wait_time}s")

    def save_image_result(self, result: Dict[str, Any], output_path: str) -> None:
        """Extract Base64 image from result and save to file."""
        output = result.get("output", {})
        image_data = output.get("image", "")
        if not image_data:
            raise ValueError("No image data in result")

        if "," in image_data:
            image_data = image_data.split(",", 1)[1]

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(image_data))
        logger.info(f"Image saved: {output_path}")

    def create_image(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        seed: int = 42,
        guidance: float = 3.5,
        ip_adapter_weight: float = 0.8,
        quality: int = 90,
        lora_pairs: Optional[List[Dict[str, Any]]] = None,
        check_interval: int = 5,
        max_wait_time: int = 300,
    ) -> Dict[str, Any]:
        """Generate an image from reference image and prompt.

        Args:
            prompt: Text prompt for image generation.
            image_path: Local path to reference image (will be Base64 encoded).
            image_url: URL to reference image.
            image_base64: Base64-encoded reference image.
            negative_prompt: Negative prompt (uses default if None).
            width: Output image width (rounded to nearest 16).
            height: Output image height (rounded to nearest 16).
            steps: Number of inference steps (1-100).
            seed: Random seed for reproducibility.
            guidance: Guidance scale for FLUX.
            ip_adapter_weight: IP-Adapter influence (0.0-2.0).
            quality: JPEG quality (1-100).
            lora_pairs: List of LoRA configs [{"name": "...", "weight": 1.0}].
            check_interval: Seconds between status polls.
            max_wait_time: Max seconds to wait for completion.

        Returns:
            RunPod result dict with output.image (Base64 JPEG).
        """
        input_data: Dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "seed": seed,
            "guidance": guidance,
            "ip_adapter_weight": ip_adapter_weight,
            "quality": quality,
        }

        if negative_prompt is not None:
            input_data["negative_prompt"] = negative_prompt

        if image_path:
            input_data["image_base64"] = self.encode_file_to_base64(image_path)
        elif image_url:
            input_data["image_url"] = image_url
        elif image_base64:
            input_data["image_base64"] = image_base64
        else:
            raise ValueError("Reference image required: image_path, image_url, or image_base64")

        if lora_pairs:
            input_data["lora_pairs"] = lora_pairs

        job_id = self.submit_job(input_data)
        return self.wait_for_completion(job_id, check_interval, max_wait_time)


if __name__ == "__main__":
    from dotenv import load_dotenv

    logging.basicConfig(level=logging.INFO)
    load_dotenv()

    client = GenerateImageClient(
        runpod_endpoint_id=os.environ["RUNPOD_ENDPOINT_ID"],
        runpod_api_key=os.environ["RUNPOD_API_KEY"],
    )

    # Basic usage
    result = client.create_image(
        image_path="./example_image.png",
        prompt="a beautiful anime girl in a garden, detailed, high quality",
        width=1024,
        height=1024,
    )
    client.save_image_result(result, "./output.jpg")

    # With LoRA
    # result = client.create_image(
    #     image_path="./example_image.png",
    #     prompt="a beautiful anime girl in a garden",
    #     lora_pairs=[{"name": "style_lora.safetensors", "weight": 0.8}],
    # )
    # client.save_image_result(result, "./output_lora.jpg")
