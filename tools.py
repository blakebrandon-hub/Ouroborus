"""
Ouroboros — Tools
Web search and Python function execution
"""

import sys
import io
import traceback
import requests
import re
import time
import datetime
from bs4 import BeautifulSoup as bs4
import numpy as np
from supabase_client import recall, recall_all, remember, forget, get_function


# ─────────────────────────────────────────────────────────────────────────────
# WEB SEARCH
# ─────────────────────────────────────────────────────────────────────────────

def web_search(query: str) -> str:
    """Search the web using DuckDuckGo instant answer API"""
    try:
        response = requests.get(
            'https://api.duckduckgo.com/',
            params={
                'q': query,
                'format': 'json',
                'no_html': 1,
                'skip_disambig': 1
            },
            timeout=10
        )
        data = response.json()

        results = []

        # Abstract (main answer)
        if data.get('Abstract'):
            results.append(f"Summary: {data['Abstract']}")
            if data.get('AbstractURL'):
                results.append(f"Source: {data['AbstractURL']}")

        # Instant answer
        if data.get('Answer'):
            results.append(f"Answer: {data['Answer']}")

        # Related topics
        topics = data.get('RelatedTopics', [])[:3]
        for topic in topics:
            if isinstance(topic, dict) and topic.get('Text'):
                results.append(f"• {topic['Text']}")

        if results:
            return '\n'.join(results)
        else:
            return f"No direct results found for: {query}"

    except Exception as e:
        return f"Search error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# PYTHON EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

# Sandbox globals — what Ouroboros can access when running code
SANDBOX_GLOBALS = {
    '__builtins__': {
        '__import__': __import__,
        'open': open,
        'print': print,
        'len': len,
        'range': range,
        'remember': remember,
        'forget': forget,
        'enumerate': enumerate,
        'zip': zip,
        'map': map,
        'filter': filter,
        'sorted': sorted,
        'list': list,
        'dict': dict,
        'set': set,
        'tuple': tuple,
        'str': str,
        'int': int,
        'float': float,
        'bool': bool,
        'type': type,
        'isinstance': isinstance,
        'hasattr': hasattr,
        'getattr': getattr,
        'recall': recall,
        'recall_all': recall_all,
        'sum': sum,
        'min': min,
        'max': max,
        'abs': abs,
        'round': round,
        'any': any,
        'all': all,
        'repr': repr,
        'reversed': reversed,
        'Exception': Exception,
        'ValueError': ValueError,
        'TypeError': TypeError,
        'KeyError': KeyError,
    },
    're': re,
    'requests': requests,
    'datetime': datetime,
    'time': time,
    'bs4': bs4,
    'BeautifulSoup': bs4,
    'np': np,
    'numpy': np,
}


def execute_python(code: str) -> str:
    """
    Execute Python code in a sandboxed environment.
    Returns stdout output or error message.
    """
    stdout_capture = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout_capture

    try:
        exec(code, SANDBOX_GLOBALS.copy())
        output = stdout_capture.getvalue()
        return output if output else "(no output)"
    except Exception as e:
        return f"Error: {traceback.format_exc()}"
    finally:
        sys.stdout = old_stdout


def call_saved_function(name: str, **kwargs) -> str:
    """
    Call a saved function by name with optional parameters.
    Returns stdout output and/or return value.
    """
    fn = get_function(name)
    if not fn:
        return f"Error: function '{name}' not found"

    code = fn['code']
    sandbox = SANDBOX_GLOBALS.copy()
    sandbox.update(kwargs)

    stdout_capture = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout_capture

    try:
        local_vars = {}
        exec(code, sandbox, local_vars)
        output = stdout_capture.getvalue()
        
        # If function was defined and is callable, try to call it
        fn_name = name
        if fn_name in local_vars and callable(local_vars[fn_name]):
            result = local_vars[fn_name](**kwargs)
            if result is not None:
                output += str(result) + '\n'
        
        return output if output else "(no output)"
    except Exception as e:
        return f"Error: {traceback.format_exc()}"
    finally:
        sys.stdout = old_stdout
