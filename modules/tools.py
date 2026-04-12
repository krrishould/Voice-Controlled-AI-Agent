import os
import ollama

MODEL = "llama3.2"      # must match the model you pulled via Ollama

OUTPUT_DIR = "output"


def execute_tool(intent_data: dict, transcript: str, context_text: str = "", chat_messages: list = []) -> dict:
    """
    Routes to the correct tool based on detected intent.
    All file operations are confined to the output/ directory.
    context_text:   optional text pasted/uploaded by the user to act on.
    chat_messages:  prior conversation turns as [{"role": ..., "content": ...}, ...]
    Returns a dict with: action, output, file_path
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    intent = intent_data.get("intent", "general_chat")

    if intent == "create_file":
        return _create_file(intent_data)
    elif intent == "write_code":
        return _write_code(intent_data, transcript, chat_messages)
    elif intent == "summarize":
        return _summarize(transcript, context_text, chat_messages)
    else:
        return _general_chat(transcript, context_text, chat_messages)


def _create_file(intent_data: dict) -> dict:
    filename  = intent_data.get("filename") or "new_file.txt"
    file_path = os.path.join(OUTPUT_DIR, filename)

    with open(file_path, "w") as f:
        f.write("")

    return {
        "action":    f"Created file `{filename}` in output/",
        "output":    f"Empty file `{filename}` has been created successfully.",
        "file_path": file_path,
    }


def _write_code(intent_data: dict, transcript: str, chat_messages: list = []) -> dict:
    filename = intent_data.get("filename") or "generated_code.py"

    system_msg = {
        "role":    "system",
        "content": (
            "You are a coding assistant. Write clean, working code based on the user's request. "
            "Use prior conversation context if the user refers to something discussed earlier. "
            "Return ONLY the raw code — no markdown fences, no explanation."
        ),
    }
    messages = [system_msg] + chat_messages + [{"role": "user", "content": transcript}]

    response = ollama.chat(
        model=MODEL,
        messages=messages,
    )

    code = response.message.content.strip()

    # Strip markdown fences if the model added them anyway
    if code.startswith("```"):
        lines = code.splitlines()
        code  = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    file_path = os.path.join(OUTPUT_DIR, filename)
    with open(file_path, "w") as f:
        f.write(code)

    return {
        "action":    f"Generated code saved to `output/{filename}`",
        "output":    code,
        "file_path": file_path,
    }


def _summarize(transcript: str, context_text: str = "", chat_messages: list = []) -> dict:
    # Use the pasted/uploaded text if provided; fall back to the voice transcript
    content_to_summarize = context_text.strip() if context_text.strip() else transcript

    system_msg = {"role": "system", "content": "Summarize the following text clearly and concisely."}
    messages = [system_msg] + chat_messages + [{"role": "user", "content": content_to_summarize}]

    response = ollama.chat(
        model=MODEL,
        messages=messages,
    )

    summary   = response.message.content.strip()
    file_path = os.path.join(OUTPUT_DIR, "summary.txt")

    with open(file_path, "w") as f:
        f.write(summary)

    return {
        "action":    "Summarized text and saved to `output/summary.txt`",
        "output":    summary,
        "file_path": file_path,
    }


def _general_chat(transcript: str, context_text: str = "", chat_messages: list = []) -> dict:
    # If the user provided extra context text, include it with the voice command
    if context_text.strip():
        user_message = f"{transcript}\n\nContext:\n{context_text.strip()}"
    else:
        user_message = transcript

    system_msg = {
        "role":    "system",
        "content": (
            "You are a helpful AI assistant. Answer concisely. "
            "Remember all prior conversation turns in this session and use them when the user refers back to something."
        ),
    }
    messages = [system_msg] + chat_messages + [{"role": "user", "content": user_message}]

    response = ollama.chat(
        model=MODEL,
        messages=messages,
    )

    return {
        "action":    "Responded to general chat",
        "output":    response.message.content.strip(),
        "file_path": None,
    }
