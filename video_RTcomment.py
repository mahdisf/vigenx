import google.generativeai as genai
import time
import os

def annotate_video_with_comments( video_path: str,
    api_key: str= os.environ["GOOGLE_API_KEY"]) -> dict:
    """
    Uploads a video to Gemini and returns timestamped 2-word comments with emojis.
    Format: {second: "comment", "emoji"}
    """
    # 🔑 Authenticate
    genai.configure(api_key=api_key)
    client = genai.Client()

    # 📁 Upload video
    video_file = client.files.upload(file=video_path)

    # ⏳ Wait for processing
    while video_file.state.name == "PROCESSING":
        time.sleep(5)
        video_file = client.files.get(name=video_file.name)

    # 🧠 Prompt Gemini
    prompt = (
        "Watch this video and identify key moments that stand out visually or emotionally. "
        "For each moment, provide a short 2-word comment that describes the scene, along with a relevant emoji. "
        "Return the result in this format: {second: \"comment\", \"emoji\"}. "
        "Focus on clarity, variety, and emotional resonance. Only include timestamps where something notable happens."
    )

    response = client.models.generate_content(
        model="gemini-2-Flash-Lite",
        contents=[video_file, prompt]
    )

    # 🧾 Parse and return result
    return response.text  # You can use json.loads() if the output is valid JSON
