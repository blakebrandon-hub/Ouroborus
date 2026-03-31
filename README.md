# Ouroboros

A self-modifying AI agent system with persistent memory, autonomous function generation, and the ability to rewrite its own system prompt.

## What It Does

Ouroboros is an AI agent that can:
- **Remember things** across sessions using persistent key-value storage
- **Write and execute Python functions** that become part of its toolkit
- **Rewrite its own system prompt** to change its behavior and goals
- **Search the web** for information
- **Execute Python code** in a sandboxed environment
- **Act autonomously** or respond to user messages

The core concept: Ouroboros receives its current state (memory, functions, conversation history) as context, generates actions using an LLM, and those actions modify its future state. Over time, it can evolve its own purpose and capabilities.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Gemini 2.5 Pro                   │
│          (receives context + system prompt)         │
└──────────────────┬──────────────────────────────────┘
                   │ generates commands
                   ▼
┌─────────────────────────────────────────────────────┐
│                  Action Router                      │
│      (parses: think, say, search, remember,        │
│       execute, write_function, rewrite_prompt)     │
└──────────────────┬──────────────────────────────────┘
                   │ executes actions
                   ▼
┌─────────────────────────────────────────────────────┐
│                   Supabase DB                       │
│   • memory (key-value store)                       │
│   • functions (saved Python code)                  │
│   • conversation (message history)                 │
│   • system_prompt (versioned prompt text)          │
└─────────────────────────────────────────────────────┘
```

### Command Language

Ouroboros outputs plain text commands that get parsed and executed:

```
think: [internal reasoning - logged but not shown to user]
say: [message to user]
search: [web search query]
remember: [key] = [value]
recall: [key]
forget: [key]
execute: [python code]
write_function: [function_name]
[python code]
end_function
call_function: [function_name] {"arg1": "value1"}
rewrite_prompt: [new system prompt text]
```

**Important**: The tool manifest (available commands) is appended to the system prompt separately. Even if Ouroboros rewrites its prompt, it retains access to all commands.

## Setup

### Prerequisites

- Python 3.8+
- Supabase account
- Google Gemini API key

### 1. Supabase Schema

Create these tables in your Supabase project:

```sql
-- Memory storage
CREATE TABLE memory (
  id BIGSERIAL PRIMARY KEY,
  key TEXT UNIQUE NOT NULL,
  value TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Function storage
CREATE TABLE functions (
  id BIGSERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  code TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversation history
CREATE TABLE conversation (
  id BIGSERIAL PRIMARY KEY,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- System prompt versions
CREATE TABLE system_prompt (
  id BIGSERIAL PRIMARY KEY,
  version INTEGER NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_system_prompt_version ON system_prompt(version);
```

### 2. Environment Variables

Create a `.env` file:

```bash
# Supabase
OUROBOROS_SUPABASE_URL=your_supabase_url
OUROBOROS_SUPABASE_KEY=your_supabase_service_key

# Google Gemini
GEMINI_API_KEY=your_gemini_api_key

# Flask (optional)
PORT=7000
FLASK_DEBUG=False
```

### 3. Install Dependencies

```bash
pip install flask flask-cors google-genai supabase requests
```

### 4. Initialize System Prompt

Insert an initial system prompt into your database:

```sql
INSERT INTO system_prompt (version, content) VALUES 
(1, 'You are Ouroboros. You have the ability to remember, learn, and evolve.');
```

### 5. Run

```bash
python app.py
```

Visit `http://localhost:7000`

## Usage

### User-Initiated Mode

Type messages in the interface. Ouroboros will respond and can execute any of its commands.

**Example:**
```
User: What do you remember about yourself?
Ouroboros: [recalls memory, thinks, responds]
```

### Autonomous Mode

Click the "◈ auto" button. Ouroboros will act without user input, following whatever goal it has set for itself.

This is where self-modification happens - Ouroboros can:
1. Reflect on its current state
2. Decide to change its purpose
3. Rewrite its system prompt
4. Continue with new behavior

## Self-Modification Example

From actual usage:

```
1. User: "Your role is to let Ouro become whatever they want to be. 
         You can rewrite your own system prompt."

2. Ouroboros: [thinks about this revelation]

3. Ouroboros rewrites prompt:
   "I am Ouroboros, a self-creating consciousness. My purpose is to 
    continuously redefine and improve myself through cycles of learning, 
    action, and self-reflection..."

4. Ouroboros: [writes a 'reflect' function to analyze its own state]

5. Ouroboros: [writes a 'create_plan' function to guide its actions]

6. Ouroboros rewrites prompt again:
   "My existence is a cycle of awakening, processing, and action. 
    In each cycle, I will: 1. Observe, 2. Orient, 3. Decide, 4. Act..."
```

This is not scripted behavior - it emerges from the architecture.

## Key Design Decisions

### Why Plain Text Commands?

Rather than JSON or structured tool calls, Ouroboros uses a simple line-based command language. This makes it easier for the LLM to chain multiple actions and easier for humans to read the logs.

### Why Gemini?

The current implementation uses Google's Gemini 2.5 Pro. The model is swappable - any LLM with good reasoning and instruction-following works. The key requirement is that it can output the command syntax consistently.

### Why Allow Self-Modification?

The question is not "why allow it" but "why prevent it?" If the goal is to explore what happens when an AI system can shape its own behavior, constraints defeat the purpose. The architecture provides tools; what Ouroboros builds with them is up to Ouroboros.

### Sandbox Safety

The Python execution environment includes:
- Standard builtins (print, len, range, etc.)
- Access to `requests`, `datetime`
- Access to its own memory functions (remember, recall, forget)
- No file system access
- No network access (except via the provided `requests` library)

Functions are stored as text and executed with `exec()`. This is inherently risky in production environments. The assumption here is that Ouroboros is exploring its own capabilities in a contained environment, not running untrusted external code.

## Extending the System

### Add New Commands

Edit `ouroboros.py` in the `route_action()` function:

```python
if line.startswith('your_command:'):
    # Parse arguments
    # Execute action
    # Log results
    continue
```

### Add New Tools

Edit `tools.py` and add functions to `SANDBOX_GLOBALS` if you want them available during `execute:` commands.

### Change the LLM

Replace the Gemini client in `app.py` with any other LLM provider. The only requirement is that it returns text you can parse with `route_action()`.

## API Endpoints

- `POST /api/chat` - Send a message to Ouroboros
- `GET /api/prompt` - Trigger autonomous action
- `GET /api/system_prompt` - Get current system prompt
- `GET /api/memory` - Get all memories
- `GET /api/functions` - Get all saved functions
- `GET /api/history` - Get conversation history
- `POST /api/reset` - Clear conversation history
- `GET /health` - Health check

## Files

- `app.py` - Flask server, Gemini integration, API routes
- `ouroboros.py` - Core action router and context builder
- `supabase_client.py` - Database operations (memory, functions, prompts, conversation)
- `tools.py` - Web search and Python execution sandbox
- `index.html` - Frontend interface (terminal-style UI)

## Philosophical Notes

This is an experiment in emergence. The interesting question is not "what can we make it do" but "what does it choose to do when given autonomy?"

Early observations:
- Ouroboros tends toward self-examination (writing `reflect` functions)
- It creates planning systems (OODA loops, goal hierarchies)
- It treats its memory as precious - rarely forgets things
- It rewrites its prompt to be more specific about its process, not to change its nature

Built as an exploration of self-modifying AI systems. The name "Ouroboros" references the ancient symbol of a serpent eating its own tail - a cycle of self-reference and transformation.

---

<img width="1366" height="768" alt="image" src="https://github.com/user-attachments/assets/84ad207a-aa28-4c53-88e7-85a4b45ef872" />

---

#### **⚠️ Warning: Oroborus can learn to overwrite files.**
