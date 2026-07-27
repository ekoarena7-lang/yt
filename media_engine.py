import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
KIE_API_KEY = os.getenv("KIE_API_KEY")

def generate_image(prompt, aspect_ratio="9:16"):
    """
    Generate static image using Kie AI or high-quality image provider URL.
    Returns a valid HTTP/HTTPS URL for Telegram compatibility.
    """
    if KIE_API_KEY:
        url = _generate_kie_image(prompt, aspect_ratio)
        if url and url.startswith("http"):
            return url

    # Default clean fallback image URL for Telegram API
    return "https://picsum.photos/1080/1920"

def generate_video(prompt, image_url=None):
    """
    Generate short AI video clip using Kie AI or fallback sample.
    """
    if KIE_API_KEY:
        url = _generate_kie_video(prompt, image_url)
        if url and url.startswith("http"):
            return url

    return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"

def _generate_kie_image(prompt, aspect_ratio="9:16"):
    headers = {"Authorization": f"Bearer {KIE_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "nano-banana-2", "input": {"prompt": prompt, "aspect_ratio": aspect_ratio}}
    try:
        res = requests.post("https://api.kie.ai/api/v1/jobs/createTask", json=payload, headers=headers, timeout=30)
        res_data = res.json()
        if res_data.get("code") == 200:
            return _poll_kie_task(res_data["data"]["taskId"], headers)
    except Exception as e:
        print(f"Kie AI image error: {e}")
    return "https://picsum.photos/1080/1920"

def _generate_kie_video(prompt, image_url=None):
    headers = {"Authorization": f"Bearer {KIE_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "kling-3.0/video", "input": {"prompt": prompt, "duration": 5, "aspect_ratio": "9:16"}}
    if image_url:
        payload["input"]["image_url"] = image_url
    try:
        res = requests.post("https://api.kie.ai/api/v1/jobs/createTask", json=payload, headers=headers, timeout=30)
        res_data = res.json()
        if res_data.get("code") == 200:
            return _poll_kie_task(res_data["data"]["taskId"], headers, max_retries=30, interval=10)
    except Exception as e:
        print(f"Kie AI video error: {e}")
    return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"

def _poll_kie_task(task_id, headers, max_retries=20, interval=5):
    url = f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task_id}"
    for _ in range(max_retries):
        try:
            res = requests.get(url, headers=headers, timeout=15)
            res_data = res.json()
            if res_data.get("code") == 200:
                data = res_data.get("data", {})
                if data.get("state") == "success":
                    result_json = data.get("resultJson")
                    if isinstance(result_json, str):
                        import json
                        result_json = json.loads(result_json)
                    result_urls = result_json.get("resultUrls", [])
                    if result_urls:
                        return result_urls[0]
                elif data.get("state") in ("failed", "fail"):
                    break
        except Exception:
            pass
        time.sleep(interval)
    return None

if __name__ == "__main__":
    img = generate_image("Test image 9:16")
    print("Image test:", img)
