# Install these: pip install flask openai python-dotenv
from flask import Flask, request, jsonify
import openai
import os
import base64 # Needed for decoding image on server side
import io # Needed for PIL image handling
from PIL import Image
import time

app = Flask(__name__)

# Load API key from environment variable (CRUCIAL FOR VERECEL)
# Set OPENAI_API_KEY in your Vercel project settings 
openai.api_key =  os.getenv("OPENAI_API_KEY")
MIN_TIME_BETWEEN_LLM_CALLS_SERVER = 3.0 # <--- ADD THIS (Adjust as needed for your specific OpenAI limit)
last_llm_call_time_server = 0 # <--- ADD THIS

@app.route('/get_ai_action', methods=['POST'])
def get_ai_action():
    global last_llm_call_time_server # <--- IMPORTANT: Declare global

    current_time = time.time()
    if (current_time - last_llm_call_time_server) < MIN_TIME_BETWEEN_LLM_CALLS_SERVER:
        # If hit rate limit on server, respond with 'WAIT' and a helpful message
        return jsonify({
            "action": "WAIT",
            "message": f"Server-side throttling: Next OpenAI call allowed in {MIN_TIME_BETWEEN_LLM_CALLS_SERVER - (current_time - last_llm_call_time_server):.2f}s"
        }), 200 # Return 200 OK because 'WAIT' is a valid action

    data = request.json
    context_prompt = data.get("context_prompt", "")
    history = data.get("history", "")
    image_base64 = data.get("image_base64", "")

    messages_content = []
    messages_content.append({"type": "text", "text": f"You are playing a browser game. Your name is Tofucha. Previous actions/states: {history}\n\n{context_prompt} What is the single best action to take now? Respond ONLY with one of these commands: 'MOVE_UP', 'MOVE_DOWN', 'MOVE_LEFT', 'MOVE_RIGHT', 'ATTACK', 'USE_E', 'USE_G', 'WAIT', 'CHAT_MESSAGE:<your_message>', 'CLICK_X_Y'. Example: 'MOVE_RIGHT' or 'CHAT_MESSAGE:Hello world!'"})

    if image_base64:
        messages_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{image_base64}"
            }
        })

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": messages_content}],
            max_tokens=50
        )
        action_command = response.choices[0].message.content.strip().upper()
        last_llm_call_time_server = time.time() # <--- Update time only on success

        return jsonify({"action": action_command})

    except openai.APIError as e:
        # Handle specific OpenAI API errors, e.g., rate limits, invalid keys
        print(f"OpenAI API Error on Vercel: {e}")
        # If it's a 429 (rate limit), you might want to specifically log or return a different message
        if e.status == 429:
            return jsonify({"action": "WAIT", "message": "OpenAI rate limit hit on server."}), 200
        return jsonify({"action": "ERROR", "message": f"OpenAI API Error: {e.status} {e.message}"}), 500
    except Exception as e:
        print(f"Error processing request on Vercel: {e}")
        return jsonify({"action": "ERROR", "message": f"Server error: {e}"}), 500

    
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Vercel API proxy is running."}), 200


if __name__ == '__main__':
    # This block is for local testing only
    # On Vercel, this app will be run by their serverless infrastructure
    app.run(debug=True)
