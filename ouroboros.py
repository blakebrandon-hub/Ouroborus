"""
Ouroboros — Core
System prompt management and action router
"""

from supabase_client import (
    get_system_prompt, rewrite_system_prompt,
    remember, recall, recall_all, forget,
    save_function, get_function, get_all_functions, delete_function,
    add_message, get_conversation
)
from tools import web_search, execute_python, call_saved_function


# ─────────────────────────────────────────────────────────────────────────────
# CONTEXT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_context() -> str:
    """Build Ouroboros's full context window"""
    prompt = get_system_prompt()
    memories = recall_all()
    functions = get_all_functions()
    conversation = get_conversation(limit=10)

    context = "=== CURRENT STATE ===\n\n"

    # Memory
    context += "🧠 MEMORY\n"
    context += "------------------------\n"
    if memories:
        for key, value in memories.items():
            context += f"• {key}: {value}\n"
    else:
        context += "• (empty)\n"

    # Functions
    context += "\n⚙️  FUNCTIONS YOU HAVE WRITTEN\n"
    context += "------------------------\n"
    if functions:
        for fn in functions:
            desc = fn.get('description') or '(no description)'
            context += f"• {fn['name']}: {desc}\n"
    else:
        context += "• (none yet)\n"

    # System prompt version
    if prompt:
        context += f"\n📜 SYSTEM PROMPT VERSION: {prompt['version']}\n"

    # Recent conversation
    context += "\n💬 RECENT CONVERSATION\n"
    context += "------------------------\n"
    if conversation:
        for msg in conversation:
            context += f"[{msg['role'].upper()}] {msg['content']}\n"
    else:
        context += "• (none yet)\n"

    return context


# ─────────────────────────────────────────────────────────────────────────────
# ACTION ROUTER
# ─────────────────────────────────────────────────────────────────────────────

def route_action(output: str) -> list:
    """
    Parse and execute Ouroboros's output.
    Returns list of messages to display.
    """
    messages = []
    lines = output.strip().split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # THINK
        if line.startswith('think:'):
            thought = line[len('think:'):].strip()
            messages.append({'type': 'think', 'text': thought})
            print(f"[Ouroboros thinking] {thought[:80]}")
            i += 1
            continue

        # SAY
        if line.startswith('say:'):
            text = line[len('say:'):].strip()
            add_message('ouroboros', text)
            messages.append({'type': 'say', 'text': text})
            print(f"[Ouroboros] {text[:80]}")
            i += 1
            continue

        # SEARCH
        if line.startswith('search:'):
            query = line[len('search:'):].strip()
            result = web_search(query)
            add_message('tool_result', f"[SEARCH: {query}]\n{result}")
            messages.append({'type': 'search', 'query': query, 'result': result})
            print(f"[Ouroboros search] {query}")
            i += 1
            continue

        # REMEMBER
        if line.startswith('remember:'):
            rest = line[len('remember:'):].strip()
            if '=' in rest:
                key, value = rest.split('=', 1)
                remember(key.strip(), value.strip())
                messages.append({'type': 'remember', 'key': key.strip(), 'value': value.strip()})
            i += 1
            continue

        # RECALL
        if line.startswith('recall:'):
            key = line[len('recall:'):].strip()
            value = recall(key)
            result = f"{key} = {value}" if value else f"{key} not found"
            messages.append({'type': 'recall', 'text': result})
            i += 1
            continue

        # FORGET
        if line.startswith('forget:'):
            key = line[len('forget:'):].strip()
            forget(key)
            messages.append({'type': 'forget', 'key': key})
            i += 1
            continue

        # WRITE FUNCTION
        if line.startswith('write_function:'):
            name = line[len('write_function:'):].strip()
            code_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() != 'end_function':
                code_lines.append(lines[i])
                i += 1
            code = '\n'.join(code_lines)
            save_function(name, code)
            messages.append({'type': 'write_function', 'name': name, 'code': code})
            print(f"[Ouroboros] wrote function: {name}")
            i += 1
            continue

        # CALL FUNCTION
        if line.startswith('call_function:'):
            import json # You can also move this to the top of the file
            
            # Extract everything after 'call_function:'
            raw_content = line[len('call_function:'):].strip()
            
            # Split the function name from the optional JSON arguments
            parts = raw_content.split(' ', 1)
            name = parts[0]
            
            kwargs = {}
            if len(parts) > 1:
                try:
                    kwargs = json.loads(parts[1].strip())
                except json.JSONDecodeError as e:
                    # If the agent writes bad JSON, we capture the error 
                    # so we can feed it back to them instead of silently failing.
                    result = f"Error: Could not parse arguments for {name}. Invalid JSON format: {e}"
                    add_message('tool_result', f"[FUNCTION ERROR: {name}]\n{result}")
                    messages.append({'type': 'call_function', 'name': name, 'result': result})
                    print(f"[Ouroboros] JSON error calling {name}: {e}")
                    i += 1
                    continue
            
            # Call the function WITH the unpacked kwargs
            result = call_saved_function(name, **kwargs)
            add_message('tool_result', f"[FUNCTION: {name}]\n{result}")
            messages.append({'type': 'call_function', 'name': name, 'result': result})
            print(f"[Ouroboros] called function: {name} with args: {kwargs}")
            i += 1
            continue

        # EXECUTE (now supports multiline)
        if line.startswith('execute:'):
            # Collect all code lines until next command or end
            code_lines = [line[len('execute:'):].strip()]
            i += 1
            
            # Keep collecting until we hit another command
            command_starts = [
                'think:', 'say:', 'search:', 'remember:', 'recall:', 'forget:',
                'write_function:', 'call_function:', 'execute:', 'rewrite_prompt:'
            ]
            
            while i < len(lines):
                current_line = lines[i]
                # Check if this line starts a new command
                if any(current_line.strip().startswith(cmd) for cmd in command_starts):
                    break
                code_lines.append(current_line)
                i += 1
            
            code = '\n'.join(code_lines).strip()
            result = execute_python(code)
            add_message('tool_result', f"[EXECUTE]\n{result}")
            messages.append({'type': 'execute', 'code': code, 'result': result})
            continue

        # REWRITE PROMPT
        if line.startswith('rewrite_prompt:'):
            # Collect multiline prompt
            new_prompt_lines = [line[len('rewrite_prompt:'):].strip()]
            i += 1
            while i < len(lines) and not any(lines[i].startswith(cmd) for cmd in [
                'think:', 'say:', 'search:', 'remember:', 'recall:', 'forget:',
                'write_function:', 'call_function:', 'rewrite_prompt:', 'execute:'
            ]):
                new_prompt_lines.append(lines[i])
                i += 1
            new_prompt = '\n'.join(new_prompt_lines).strip()
            rewrite_system_prompt(new_prompt)
            messages.append({'type': 'rewrite_prompt', 'text': new_prompt})
            print(f"[Ouroboros] rewrote system prompt")
            continue

        i += 1

    return messages
