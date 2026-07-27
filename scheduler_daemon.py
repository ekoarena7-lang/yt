import time
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(__file__))

from db.database import init_db, get_pending_scheduled_posts, update_post_status
from core.social_publisher import publish_to_platforms

load_dotenv()

def run_scheduler_loop(poll_interval=30):
    init_db()
    print(f"🤖 YİTX Otomasyonu Scheduler Daemon started (Polling every {poll_interval}s)...")

    while True:
        try:
            pending_posts = get_pending_scheduled_posts()
            if pending_posts:
                print(f"Found {len(pending_posts)} post(s) ready to publish.")
                for post in pending_posts:
                    post_id = post["id"]
                    text = post["content_text"]
                    media = post["media_url"]
                    platforms = post["platforms"]

                    print(f"Publishing Post #{post_id} to [{platforms}]...")
                    res = publish_to_platforms(text, media, platforms)
                    
                    success = any(v.get("status") == "success" for v in res.values())
                    if success:
                        update_post_status(post_id, "published", error_log=str(res))
                        print(f"Post #{post_id} successfully published!")
                    else:
                        update_post_status(post_id, "failed", error_log=str(res))
                        print(f"Post #{post_id} publishing failed.")
            else:
                pass
        except Exception as e:
            print(f"Scheduler error: {e}")
        
        time.sleep(poll_interval)

if __name__ == "__main__":
    run_scheduler_loop(poll_interval=10)
