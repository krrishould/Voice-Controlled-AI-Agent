import os
import ollama

MODEL = "llama3.2"      # must match the model you pulled via Ollama

OUTPUT_DIR = "output"


def execute_tool(intent_data: dict, transcript: str) -> dict:
    """
    Routes to the correct tool based on detected intent.
    All file operations are confined to the output/ directory.
    Returns a dict with: action, output, file_path
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    intent = intent_data.get("intent", "general_chat")

    if intent == "create_file":
        return _create_file(intent_data)
    elif intent == "write_code":
        return _write_code(intent_data, transcript)
    elif intent == "summarize":
        return _summarize(transcript)
    else:
        return _general_chat(transcript)


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


def _write_code(intent_data: dict, transcript: str) -> dict:
    filename = intent_data.get("filename") or "generated_code.py"

    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role":    "system",
                "content": (
                    "You are a coding assistant. Write clean, working code based on the user's request. "
                    "Return ONLY the raw code — no markdown fences, no explanation."
                ),
            },
            {"role": "user", "content": transcript},
        ],
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


def _summarize(transcript: str) -> dict:
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Summarize the following text clearly and concisely."},
            {"role": "user",   "content": transcript},
        ],
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


def _general_chat(transcript: str) -> dict:
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant. Answer concisely."},
            {"role": "user",   "content": transcript},
        ],
    )

    return {
        "action":    "Responded to general chat",
        "output":    response.message.content.strip(),
        "file_path": None,
    }
