import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def generate_ai_text(prompt, system_instruction="Sen YİTX Otomasyonu AI kontent asistanısan. Sosyal medya için yüksek etkileşimli içerikler hazırlıyorsun."):
    """
    Generate text using Gemini API.
    """
    if not GEMINI_API_KEY:
        return {
            "hook": "🚀 YİTX Otomasyonu: AI İlə Sosyal Media İnqilabı!",
            "caption": prompt,
            "hashtags": "#YITX #Automation #AI #Content"
        }

    # Try gemini-2.0-flash first, then gemini-1.5-flash as fallback
    models = ["gemini-2.0-flash", "gemini-1.5-flash"]
    
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_instruction}\n\nİstək/Konu: {prompt}\n\nLütfən cavabı JSON formatında qaytar:\n{{\"hook\": \"...\", \"caption\": \"...\", \"hashtags\": \"...\"}}"}
                    ]
                }
            ]
        }
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=25)
            if response.status_code == 200:
                res_json = response.json()
                text_content = res_json['candidates'][0]['content']['parts'][0]['text']
                
                if "```json" in text_content:
                    text_content = text_content.split("```json")[1].split("```")[0].strip()
                elif "```" in text_content:
                    text_content = text_content.split("```")[1].split("```")[0].strip()

                return json.loads(text_content)
            else:
                print(f"Gemini API model {model} returned status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Error generating text with model {model}: {e}")

    return {
        "hook": f"💡 YİTX Post: {prompt[:40]}",
        "caption": f"{prompt}\n\nYİTX Otomasyonu tərəfindən emal edildi.",
        "hashtags": "#YITX #Content #AI #Automation"
    }

if __name__ == "__main__":
    res = generate_ai_text("Süni intellektlə biznes avtomatlaşdırması haqqında post yaz")
    print(json.dumps(res, ensure_ascii=False, indent=2))
