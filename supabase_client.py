"""
Ouroboros — Supabase Client
Memory, system prompt versioning, function storage, conversation history
"""

import os
from datetime import datetime
from supabase import create_client, Client

# Use environment variables in production
SUPABASE_URL = os.environ.get("OUROBOROS_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("OUROBOROS_SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────────────────────

def get_system_prompt() -> dict:
    """Get the latest system prompt"""
    try:
        result = (supabase.table('system_prompt')
                  .select('*')
                  .order('version', desc=True)
                  .limit(1)
                  .execute())
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error getting system prompt: {e}")
        return None


def rewrite_system_prompt(new_content: str) -> dict:
    """Save a new version of the system prompt"""
    try:
        current = get_system_prompt()
        new_version = (current['version'] + 1) if current else 1

        result = supabase.table('system_prompt').insert({
            'version': new_version,
            'content': new_content
        }).execute()

        print(f"📜 System prompt rewritten → version {new_version}")
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error rewriting system prompt: {e}")
        return None


def get_prompt_history() -> list:
    """Get all system prompt versions"""
    try:
        result = (supabase.table('system_prompt')
                  .select('*')
                  .order('version', desc=False)
                  .execute())
        return result.data
    except Exception as e:
        print(f"❌ Error getting prompt history: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# MEMORY
# ─────────────────────────────────────────────────────────────────────────────

def remember(key: str, value: str) -> dict:
    """Store or update a memory"""
    try:
        existing = supabase.table('memory').select('*').eq('key', key).execute()

        if existing.data:
            # Update existing memory
            result = (supabase.table('memory')
                      .update({'value': value})
                      .eq('key', key)
                      .execute())
        else:
            # Insert new memory
            result = supabase.table('memory').insert({
                'key': key,
                'value': value
            }).execute()

        print(f"🧠 Memory stored: {key} = {value[:60]}...")
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error storing memory: {e}")
        return None


def recall(key: str) -> str:
    """Retrieve a memory by key"""
    try:
        result = supabase.table('memory').select('*').eq('key', key).execute()
        if result.data:
            return result.data[0]['value']
        return None
    except Exception as e:
        print(f"❌ Error recalling memory: {e}")
        return None


def recall_all() -> dict:
    """Get all memories as a key/value dict"""
    try:
        result = supabase.table('memory').select('*').execute()
        return {row['key']: row['value'] for row in result.data}
    except Exception as e:
        print(f"❌ Error recalling all memories: {e}")
        return {}


def forget(key: str) -> bool:
    """Delete a memory"""
    try:
        supabase.table('memory').delete().eq('key', key).execute()
        print(f"🧠 Memory deleted: {key}")
        return True
    except Exception as e:
        print(f"❌ Error deleting memory: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def save_function(name: str, code: str, description: str = None) -> dict:
    """Save a function Ouroboros has written"""
    try:
        existing = supabase.table('functions').select('*').eq('name', name).execute()

        if existing.data:
            result = (supabase.table('functions')
                      .update({'code': code, 'description': description})
                      .eq('name', name)
                      .execute())
        else:
            result = supabase.table('functions').insert({
                'name': name,
                'code': code,
                'description': description
            }).execute()

        print(f"⚙️  Function saved: {name}")
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error saving function: {e}")
        return None


def get_function(name: str) -> dict:
    """Get a function by name"""
    try:
        result = supabase.table('functions').select('*').eq('name', name).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error getting function: {e}")
        return None


def get_all_functions() -> list:
    """Get all saved functions"""
    try:
        result = supabase.table('functions').select('*').order('created_at').execute()
        return result.data
    except Exception as e:
        print(f"❌ Error getting all functions: {e}")
        return []


def delete_function(name: str) -> bool:
    """Delete a function"""
    try:
        supabase.table('functions').delete().eq('name', name).execute()
        print(f"⚙️  Function deleted: {name}")
        return True
    except Exception as e:
        print(f"❌ Error deleting function: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# CONVERSATION
# ─────────────────────────────────────────────────────────────────────────────

def add_message(role: str, content: str) -> dict:
    """Add a message to conversation history"""
    try:
        result = supabase.table('conversation').insert({
            'role': role,
            'content': content
        }).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error adding message: {e}")
        return None


def get_conversation(limit: int = 20) -> list:
    """Get recent conversation history"""
    try:
        result = (supabase.table('conversation')
                  .select('*')
                  .order('created_at', desc=True)
                  .limit(limit)
                  .execute())
        entries = result.data
        entries.reverse()
        return entries
    except Exception as e:
        print(f"❌ Error getting conversation: {e}")
        return []


def clear_conversation() -> bool:
    """Clear all conversation history"""
    try:
        # Delete all records - using a condition that's always true
        supabase.table('conversation').delete().gte('created_at', '1970-01-01').execute()
        print(f"💬 Conversation cleared")
        return True
    except Exception as e:
        print(f"❌ Error clearing conversation: {e}")
        return False
