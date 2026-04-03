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
import os
import time
import requests


class GenerateImageClient:
    def __init__(self, runpod_endpoint_id: str, runpod_api_key: str):
        self.endpoint_id = runpod_endpoint_id
        self.api_key = runpod_api_key
        self.base_url = f"https://api.runpod.ai/v2/{self.endpoint_id}"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def encode_file_to_base64(self, file_path: str) -> str:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def submit_job(self, input_data: dict) -> str:
        resp = requests.post(
            f"{self.base_url}/run",
            headers=self.headers,
            json={"input": input_data},
        )
        resp.raise_for_status()
        result = resp.json()
        job_id = result.get("id")
        if not job_id:
            raise RuntimeError(f"Failed to submit job: {result}")
        print(f"Job submitted: {job_id}")
        return job_id

    def wait_for_completion(
        self, job_id: str, check_interval: int = 5, max_wait_time: int = 300
    ) -> dict:
        start = time.time()
        while time.time() - start < max_wait_time:
            resp = requests.get(
                f"{self.base_url}/status/{job_id}",
                headers=self.headers,
            )
            resp.raise_for_status()
            result = resp.json()
            status = result.get("status")

            if status == "COMPLETED":
                print(f"Job completed: {job_id}")
                return result
            elif status == "FAILED":
                raise RuntimeError(f"Job failed: {result.get('error', 'Unknown error')}")
            elif status in ("IN_QUEUE", "IN_PROGRESS"):
                print(f"Status: {status} ({int(time.time() - start)}s elapsed)")
                time.sleep(check_interval)
            else:
                print(f"Unknown status: {status}")
                time.sleep(check_interval)

        raise TimeoutError(f"Job {job_id} timed out after {max_wait_time}s")

    def save_image_result(self, result: dict, output_path: str):
        output = result.get("output", {})
        image_data = output.get("image", "")
        if not image_data:
            raise ValueError("No image data in result")

        if "," in image_data:
            image_data = image_data.split(",", 1)[1]

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(image_data))
        print(f"Image saved: {output_path}")

    def create_image(
        self,
        prompt: str,
        image_path: str = None,
        image_url: str = None,
        image_base64: str = None,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        seed: int = 42,
        guidance: float = 3.5,
        ip_adapter_weight: float = 0.8,
        quality: int = 90,
        lora_pairs: list = None,
        check_interval: int = 5,
        max_wait_time: int = 300,
    ) -> dict:
        input_data = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "seed": seed,
            "guidance": guidance,
            "ip_adapter_weight": ip_adapter_weight,
            "quality": quality,
        }

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
    load_dotenv()

    client = GenerateImageClient(
        runpod_endpoint_id=os.environ["RUNPOD_ENDPOINT_ID"],
        runpod_api_key=os.environ["RUNPOD_API_KEY"],
    )

    result = client.create_image(
        image_path="./example_image.png",
        prompt="a beautiful anime girl in a garden, detailed, high quality",
        width=1024,
        height=1024,
    )
    client.save_image_result(result, "./output.jpg")
