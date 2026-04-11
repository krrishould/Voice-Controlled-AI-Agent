import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are an intent classifier for a voice-controlled AI agent.
Analyze the user's transcribed speech and return a JSON object with exactly these keys:
- "intent": one of ["create_file", "write_code", "summarize", "general_chat"]
- "filename": suggested filename with extension if applicable, otherwise null
- "description": a concise description of what the user wants

Intent definitions:
- create_file: user wants to create an empty file or folder
- write_code: user wants code generated and saved to a file
- summarize: user wants text or content summarized
- general_chat: any other question or conversation

Return ONLY valid JSON. No explanation, no markdown."""


def detect_intent(text: str) -> dict:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)
