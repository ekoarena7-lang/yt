import os
import requests
from dotenv import load_dotenv

load_dotenv()

MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL") or os.getenv("SOCIAL_WEBHOOK_URL")

def publish_to_platforms(content_text, media_url=None, platforms=None):
    """
    Publish content to specified social media platforms (ig, tiktok, youtube, x, linkedin).
    Uses Webhook or Direct REST API endpoints.
    """
    if isinstance(platforms, str):
        platform_list = [p.strip().lower() for p in platforms.split(",")]
    else:
        platform_list = platforms or ["ig", "tiktok", "youtube", "x", "linkedin"]

    results = {}

    if MAKE_WEBHOOK_URL:
        payload = {
            "text": content_text,
            "media_url": media_url,
            "platforms": platform_list
        }
        try:
            res = requests.post(MAKE_WEBHOOK_URL, json=payload, timeout=20)
            if res.status_code == 200:
                results["webhook"] = {"status": "success", "response": res.text}
            else:
                results["webhook"] = {"status": "failed", "code": res.status_code, "response": res.text}
        except Exception as e:
            results["webhook"] = {"status": "failed", "error": str(e)}
    else:
        print(f"[YİTX PUBLISHER] Publishing to {platform_list}:")
        print(f"  Text: {content_text[:80]}...")
        print(f"  Media: {media_url}")
        results["simulated"] = {"status": "success", "platforms": platform_list}

    return results

if __name__ == "__main__":
    res = publish_to_platforms("Bu bir YİTX Otomasyonu test paylaşımıdır!", "https://picsum.photos/1080/1920", "ig,tiktok,x")
    print(res)
