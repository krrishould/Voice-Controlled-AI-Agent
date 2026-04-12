import json
import re

import ollama

# Change this to whatever model you pulled with "ollama pull <model>"
MODEL = "llama3.2"

VALID_INTENTS = {"create_file", "write_code", "summarize", "general_chat"}

SYSTEM_PROMPT = """You are an intent classifier for a voice-controlled AI agent.
Analyze the user's transcribed speech and return a JSON object with exactly these keys:
- "intent": one of ["create_file", "write_code", "summarize", "general_chat"]
- "filename": suggested filename with extension if applicable, otherwise null
- "description": a concise description of what the user wants

Intent definitions:
- create_file: user wants to create an empty file or folder
- write_code: user wants code generated, edited, or saved to a file
- summarize: user wants text or content summarized
- general_chat: any other question or conversation

Examples:
- "create a file named notes.txt" -> {"intent":"create_file","filename":"notes.txt","description":"Create an empty file named notes.txt"}
- "write python code to say hello" -> {"intent":"write_code","filename":"generated_code.py","description":"Generate Python code that says hello"}
- "summarize this paragraph" -> {"intent":"summarize","filename":null,"description":"Summarize the provided text"}
- "what is the capital of France?" -> {"intent":"general_chat","filename":null,"description":"Answer the user's question"}

Return ONLY valid JSON. No explanation, no markdown."""

FILENAME_PATTERN = re.compile(r"\b([A-Za-z0-9_.-]+\.[A-Za-z0-9]+)\b")

CODE_ACTION_WORDS = (
    "write",
    "generate",
    "create",
    "make",
    "build",
    "implement",
    "add",
    "update",
    "edit",
    "modify",
    "fix",
    "refactor",
)

CODE_OBJECT_WORDS = (
    "code",
    "script",
    "function",
    "class",
    "program",
    "app",
    "method",
    "algorithm",
    "module",
    "api",
)

CREATE_FILE_PHRASES = (
    "create file",
    "create a file",
    "make a file",
    "new file",
    "empty file",
    "create folder",
    "create a folder",
    "make folder",
    "make a folder",
    "create directory",
    "make directory",
    "touch ",
    "mkdir ",
)

SUMMARY_PHRASES = (
    "summarize",
    "summarise",
    "summary",
    "sum up",
    "tldr",
    "tl;dr",
)

LANGUAGE_DEFAULT_FILES = {
    "python": "generated_code.py",
    "javascript": "generated_code.js",
    "typescript": "generated_code.ts",
    "java": "GeneratedCode.java",
    "c++": "generated_code.cpp",
    "cpp": "generated_code.cpp",
    "c#": "GeneratedCode.cs",
    "c": "generated_code.c",
    "html": "index.html",
    "css": "styles.css",
    "sql": "query.sql",
    "bash": "script.sh",
    "shell": "script.sh",
}


def detect_intent(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        return _build_response("general_chat", None, "No input provided.")

    rule_based = _detect_rule_based_intent(text)
    if rule_based:
        return rule_based

    try:
        response = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            format="json",
            options={"temperature": 0},
        )
        payload = json.loads(response.message.content)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError, AttributeError, RuntimeError):
        return _build_response("general_chat", None, _default_description("general_chat", text))

    return _normalize_model_response(payload, text)


def _detect_rule_based_intent(text: str) -> dict | None:
    lowered = text.lower()
    filename = _extract_filename(text)

    if _looks_like_write_code(lowered, filename):
        filename = filename or _default_code_filename(lowered)
        description = _default_description("write_code", text, filename)
        return _build_response("write_code", filename, description)

    if _looks_like_create_file(lowered):
        description = _default_description("create_file", text, filename)
        return _build_response("create_file", filename, description)

    if _looks_like_summarize(lowered):
        return _build_response("summarize", None, _default_description("summarize", text))

    return None


def _looks_like_write_code(lowered: str, filename: str | None) -> bool:
    has_action = any(word in lowered for word in CODE_ACTION_WORDS)
    has_code_object = any(word in lowered for word in CODE_OBJECT_WORDS)
    mentions_language = any(_contains_term(lowered, language) for language in LANGUAGE_DEFAULT_FILES)
    has_code_filename = bool(filename and filename.lower().endswith((".py", ".js", ".ts", ".java", ".cpp", ".c", ".cs", ".html", ".css", ".sql", ".sh")))

    return (has_action and (has_code_object or mentions_language)) or (has_code_filename and has_action)


def _looks_like_create_file(lowered: str) -> bool:
    return any(phrase in lowered for phrase in CREATE_FILE_PHRASES)


def _looks_like_summarize(lowered: str) -> bool:
    return any(phrase in lowered for phrase in SUMMARY_PHRASES)


def _normalize_model_response(payload: dict, text: str) -> dict:
    if not isinstance(payload, dict):
        return _build_response("general_chat", None, _default_description("general_chat", text))

    intent = _normalize_intent(payload.get("intent"))
    filename = payload.get("filename")
    if filename:
        filename = _extract_filename(str(filename))

    if intent in {"create_file", "write_code"} and not filename:
        filename = _extract_filename(text)

    if intent == "write_code" and not filename:
        filename = _default_code_filename(text.lower())

    description = payload.get("description")
    if not description:
        description = _default_description(intent, text, filename)

    return _build_response(intent, filename, str(description))


def _normalize_intent(intent: str | None) -> str:
    if not intent:
        return "general_chat"

    normalized = str(intent).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "create": "create_file",
        "createfile": "create_file",
        "file_create": "create_file",
        "file_creation": "create_file",
        "write": "write_code",
        "code": "write_code",
        "coding": "write_code",
        "generate_code": "write_code",
        "summarise": "summarize",
        "summary": "summarize",
        "chat": "general_chat",
        "general": "general_chat",
        "conversation": "general_chat",
    }
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in VALID_INTENTS else "general_chat"


def _extract_filename(text: str) -> str | None:
    match = FILENAME_PATTERN.search(text)
    return match.group(1) if match else None


def _default_code_filename(lowered: str) -> str:
    for language, filename in LANGUAGE_DEFAULT_FILES.items():
        if _contains_term(lowered, language):
            return filename
    return "generated_code.py"


def _contains_term(text: str, term: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text))


def _default_description(intent: str, text: str, filename: str | None = None) -> str:
    if intent == "create_file":
        if filename:
            return f"Create an empty file named {filename}."
        return "Create an empty file."
    if intent == "write_code":
        if filename:
            return f"Generate code and save it to {filename}."
        return "Generate code for the user's request."
    if intent == "summarize":
        return "Summarize the provided text."
    return f"Respond to: {text}"


def _build_response(intent: str, filename: str | None, description: str) -> dict:
    return {
        "intent": intent,
        "filename": filename,
        "description": description,
        "content_hint": description,
    }
