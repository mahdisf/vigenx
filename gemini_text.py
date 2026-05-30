import os
import requests
from PIL import Image
from io import BytesIO

import google.generativeai as genai

def generate_text( prompt):
    try:
        api_key = os.environ["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except KeyError:
        print("🔴 Error: GOOGLE_API_KEY environment variable not set.")
        print("Please set the variable before running the script.")
        exit() # Exit the script if the key is not found.

    # --- 1. Prepare the Image and Model ---
    model = genai.GenerativeModel('gemini-2.5-flash')

    print("\nSending prompt to Gemini...")

    try:
        # Call the model with the combined text and image prompt
        response = model.generate_content(prompt)

        # --- 3. Print the Result ---
        print("\n--- Gemini's Response ---")
        print(response.text)
        print("-------------------------\n")

    except Exception as e:
        print(f"🔴 An error occurred while calling the API: {e}")

    return response.text


generate_text("give me a list of football player!")