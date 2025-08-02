import os
from flask import Flask, request, jsonify
import base64
from PIL import Image
import io
import time
import numpy as np

# <--- NEW/UPDATED IMPORTS FOR GEMINI --->
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
# <--- END NEW/UPDATED IMPORTS --->

app = Flask(__name__)

# --- Configure Gemini API ---
# Ensure GEMINI_API_KEY is set in Vercel environment variables 
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# --- Rate Limit Management for Vercel Function (Adjust as needed for Gemini limits) ---
MIN_TIME_BETWEEN_LLM_CALLS_SERVER = 3.0 # Start with 3 seconds, adjust based on Gemini's rate limits
last_llm_call_time_server = 0

@app.route('/api', methods=['GET'])
def home():
    return "AI Action API is running! Use POST to /api/get_ai_action.", 200

@app.route('/get_ai_action', methods=['POST'])
def get_ai_action():
    global last_llm_call_time_server

    current_time = time.time()
    if (current_time - last_llm_call_time_server) < MIN_TIME_BETWEEN_LLM_CALLS_SERVER:
        return jsonify({
            "action": "WAIT",
            "message": f"Server-side throttling: Next LLM call allowed in {MIN_TIME_BETWEEN_LLM_CALLS_SERVER - (current_time - last_llm_call_time_server):.2f}s"
        }), 200

    data = request.json
    context_prompt = data.get("context_prompt", "")
    history = data.get("history", "")
    image_base64 = data.get("image_base64", "")

    # Prepare content for Gemini
    gemini_content = []

    # Add text prompt
    gemini_content.append(f"You are playing a browser game. Your name is Tofucha. Previous actions/states: {history}\n\n{context_prompt} What is the single best action to take now? Respond ONLY with one of these commands: 'MOVE_UP', 'MOVE_DOWN', 'MOVE_LEFT', 'MOVE_RIGHT', 'ATTACK', 'USE_E', 'USE_G', 'WAIT', 'CHAT_MESSAGE:<your_message>', 'CLICK_X_Y'. Example: 'MOVE_RIGHT' or 'CHAT_MESSAGE:Hello world!'")

    # Add image if available
    if image_base64:
        try:
            # Decode base64 to bytes
            image_bytes = base64.b64decode(image_base64)
            # Create a PIL Image object from bytes
            pil_image = Image.open(io.BytesIO(image_bytes))
            
            # Gemini expects PIL Image objects directly in the content list
            gemini_content.append(pil_image)
        except Exception as e:
            print(f"Error processing image for Gemini: {e}")
            return jsonify({"action": "ERROR", "message": f"Server error processing image: {e}"}), 500

    action_command = "WAIT" # Default fallback action

    try:
        # Initialize the Gemini Pro Vision model
        model = genai.GenerativeModel('gemini-pro-vision')

        # Generate content with safety settings
        response = model.generate_content(
            gemini_content,
            generation_config={"max_output_tokens": 50}, # Similar to max_tokens in OpenAI
            safety_settings={ # Recommended safety settings to reduce blocking
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
        
        # Access the text from the response
        action_command = response.text.strip().upper()
        last_llm_call_time_server = time.time() # Update time only after successful API call

        return jsonify({"action": action_command})

    except Exception as e:
        # Catch any errors from Gemini API call
        print(f"Error calling Gemini API on Vercel: {e}")
        return jsonify({"action": "ERROR", "message": f"Gemini API Error: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True)