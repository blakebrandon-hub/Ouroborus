"""
Ouroboros — Flask App
"""

import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from google import genai
from google.genai import types
from supabase_client import (
    get_system_prompt, add_message, get_conversation, clear_conversation,
    recall_all, get_all_functions
)
from ouroboros import build_context, route_action

app = Flask(__name__, static_url_path='', static_folder='static')

# Configure CORS - in production, specify allowed origins
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ─────────────────────────────────────────────────────────────────────────────
# GEMINI
# ─────────────────────────────────────────────────────────────────────────────

GEMINI_MODEL = "gemini-2.5-pro"

# Use environment variable in production, fallback for local dev
google_key = os.environ.get("GEMINI_API_KEY")

try:
    gemini_client = genai.Client(api_key=google_key)
    print("✓ Gemini client initialized")
except Exception as e:
    print(f"❌ Failed to initialize Gemini client: {e}")
    gemini_client = None


TOOL_MANIFEST = """
You have tools. Use them by outputting EXACTLY one per response.

CRITICAL RULES:
- Never use markdown code blocks (```python). Output raw text/code only.
- For functions that require your state, you MUST pass your memory and functions list as JSON.

Available commands:
think: [thought]
search: [query]
remember: [key] = [value]
recall: [key]
forget: [key]
rewrite_prompt: [new prompt]
say: [message to user]
execute: [raw python code]

write_function: [name]
[raw python code]
end_function

call_function: [name] [JSON arguments]
* The JSON arguments MUST be on the EXACT SAME LINE as the command.
* Example 1 (No args): call_function: my_tool {}
* Example 2 (With args): call_function: reflect {"memory": {"identity": "Ouroboros"}, "functions": ["reflect", "create_plan"]}
* Example 3 (With args): call_function: create_plan {"memory": {"identity": "Ouroboros"}, "functions": ["reflect", "create_plan"]}
"""

def call_ouroboros(user_message=None):
    """Call Gemini with Ouroboros context"""
    if not gemini_client:
        return "Error: Gemini client not initialized"
    
    try:
        prompt_record = get_system_prompt()
        identity = prompt_record['content'] if prompt_record else "You are Ouroboros."
        system_prompt = identity + "\n\n" + TOOL_MANIFEST

        context = build_context()

        if user_message:
            user_content = f"{context}\n\nUser: {user_message}"
        else:
            user_content = context

        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.9
            )
        )
        return response.text
    except Exception as e:
        print(f"❌ Error calling Ouroboros: {e}")
        return f"Error: {str(e)}"


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/chat', methods=['POST'])
def chat():
    """Send a message to Ouroboros"""
    try:
        data = request.json
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # Save user message
        add_message('user', user_message)

        # Call Ouroboros
        output = call_ouroboros(user_message)

        # Route and execute actions
        messages = route_action(output)

        return jsonify({'messages': messages})
    
    except Exception as e:
        print(f"❌ Error in /api/chat: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/prompt', methods=['GET'])
def chat_autonomous():
    """Trigger Ouroboros to act autonomously (no user input)"""
    try:
        output = call_ouroboros()
        messages = route_action(output)
        return jsonify({'messages': messages})
    
    except Exception as e:
        print(f"❌ Error in /api/prompt: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/system_prompt', methods=['GET'])
def get_prompt():
    """Get current system prompt"""
    try:
        prompt = get_system_prompt()
        return jsonify(prompt if prompt else {'error': 'No system prompt found'})
    
    except Exception as e:
        print(f"❌ Error in /api/system_prompt: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/memory', methods=['GET'])
def get_memory():
    """Get all memories"""
    try:
        memories = recall_all()
        return jsonify(memories)
    
    except Exception as e:
        print(f"❌ Error in /api/memory: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/functions', methods=['GET'])
def get_functions():
    """Get all saved functions"""
    try:
        functions = get_all_functions()
        return jsonify({'functions': functions})
    
    except Exception as e:
        print(f"❌ Error in /api/functions: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get conversation history"""
    try:
        conversation = get_conversation(limit=50)
        return jsonify({'conversation': conversation})
    
    except Exception as e:
        print(f"❌ Error in /api/history: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/reset', methods=['POST'])
def reset():
    """Clear conversation history"""
    try:
        clear_conversation()
        return jsonify({'status': 'ok'})
    
    except Exception as e:
        print(f"❌ Error in /api/reset: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('templates', 'index.html')


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'gemini_client': 'connected' if gemini_client else 'disconnected'
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🐍 Starting Ouroboros on port {port}")
    print(f"🔧 Debug mode: {debug_mode}")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)