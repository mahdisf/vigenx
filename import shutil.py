import shutil
import os

cache_dir = os.path.expanduser(r"~\AppData\Local\tts")
if os.path.exists(cache_dir):
    shutil.rmtree(cache_dir)
    print("✅ Deleted old TTS cache.")
else:
    print("⚠️ No TTS cache found.")
