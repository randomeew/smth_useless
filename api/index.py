# Install these: pip install flask openai python-dotenv
from flask import Flask, request, jsonify
import openai
import os
import base64 # Needed for decoding image on server side
import io # Needed for PIL image handling
from PIL import Image

app = Flask(__name__)

# Load API key from environment variable (CRUCIAL FOR VERECEL) 
# Set OPENAI_API_KEY in your Vercel project settings 
openai.api_key = "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"#os.getenv("OPENAI_API_KEY")

@app.route('/get_ai_action', methods=['POST'])
def get_ai_action():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    context_prompt = data.get('context_prompt')
    history = data.get('history', '')
    image_base64 = data.get('image_base64') # This is the base64 string from your laptop

    if not context_prompt or not image_base64:
        return jsonify({"error": "Missing context_prompt or image_base64"}), 400

    messages_content = []

    # Add text prompt
    messages_content.append({"type": "text", "text": f"You are playing a browser game. Your name is Tofucha. Previous actions/states: {history}\n\n{context_prompt} What is the single best action to take now? Respond ONLY with one of these commands: 'MOVE_UP', 'MOVE_DOWN', 'MOVE_LEFT', 'MOVE_RIGHT', 'ATTACK', 'USE_E', 'USE_G', 'WAIT', 'CHAT_MESSAGE:<your_message>', 'CLICK_X_Y'. Example: 'MOVE_RIGHT' or 'CHAT_MESSAGE:Hello world!'"})
    
    # Add image
    messages_content.append({
        "type": "image_url",
        "image_url": {
            "url": f"data:image/png;base64,{image_base64}"
        }
    })

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": messages_content}
            ],
            max_tokens=50
        )
        action_command = response.choices[0].message.content.strip().upper()
        return jsonify({"action": action_command})

    except openai.APIError as e:
        print(f"OpenAI API Error on server: {e}")
        return jsonify({"error": f"OpenAI API Error: {str(e)}"}), 500
    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Vercel API proxy is running."}), 200


if __name__ == '__main__':
    # This block is for local testing only
    # On Vercel, this app will be run by their serverless infrastructure
    app.run(debug=True)
