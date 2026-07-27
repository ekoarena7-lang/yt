import os
import json
import re
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from core.text_generator import generate_ai_text

SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")

def extract_platform_and_id(url):
    if "youtube.com" in url or "youtu.be" in url:
        pattern = r"(?:v=|\/\|vi=|\/v\/|youtu\.be\/|\/embed\/)([a-zA-Z0-9_-]{11})"
        match = re.search(pattern, url)
        return "youtube", match.group(1) if match else None
    elif "instagram.com" in url or "instagr.am" in url:
        return "instagram", url
    elif "tiktok.com" in url:
        return "tiktok", url
    return "unknown", None

def get_transcript_or_content(source_url):
    platform, video_id = extract_platform_and_id(source_url)
    
    if platform == "youtube" and video_id:
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['az', 'tr', 'en'])
            return " ".join([item['text'] for item in transcript_list])
        except Exception as e:
            print(f"YouTube Transcript fallback: {e}")

    # If Supadata API key is available, use it for TikTok / Instagram / YouTube fallback
    if SUPADATA_API_KEY:
        headers = {"x-api-key": SUPADATA_API_KEY}
        try:
            res = requests.get(f"https://api.supadata.ai/v1/transcript?url={source_url}", headers=headers, timeout=20)
            if res.status_code == 200:
                data = res.json()
                content = data.get("content") or data.get("transcript")
                if content:
                    return content
        except Exception as e:
            print(f"Supadata extraction error: {e}")

    return f"Sosyal Medya Video Linki ({platform.upper()}): {source_url}"

def repurpose_content(source_input):
    """
    Repurpose YouTube, Instagram Reels, TikTok links OR long texts into:
    - 5 Shorts/Reels/TikTok scripts
    - 10 X (Twitter) posts
    - 3 LinkedIn articles
    """
    if source_input.startswith("http://") or source_input.startswith("https://"):
        text = get_transcript_or_content(source_input)
    else:
        text = source_input

    prompt = f"""
    Aşağıdakı video məzmununu (YouTube / Instagram / TikTok) sosial media üçün yenidən işlə (Content Repurposing - YİTX Otomasyonu):

    MƏZMUN / LİNK:
    {text[:3000]}

    XAHİŞ OLUNUR AŞAĞIDAKILARI YARAT VƏ STRUKTUR İLƏ QAYTAR:
    1. 3 ədəd Shorts/Reels/TikTok Video Ssenarisi (Hook, Səs mətni, Visual prompt)
    2. 5 ədəd X (Twitter) Postu
    3. 2 ədəd LinkedIn Məqaləsi
    """

    res = generate_ai_text(prompt, system_instruction="Sen YİTX Multi-Platform Repurposer-isən. YouTube, Instagram Reels və TikTok videolarını viral postlara çevirirsən.")
    return res

if __name__ == "__main__":
    output = repurpose_content("https://www.instagram.com/reel/C123456789")
    print(json.dumps(output, ensure_ascii=False, indent=2))
