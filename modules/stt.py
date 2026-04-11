import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Phrases Whisper commonly hallucinates on silence or background noise
_KNOWN_HALLUCINATIONS = {
    "thank you", "thanks for watching", "thank you for watching",
    "продолжение следует", "to be continued", "subtitles by",
    "subscribe", "please subscribe", "like and subscribe",
    "you", "bye", "okay", "ok", "hmm", "um", "uh",
    ".", "..", "...",
}


def transcribe_audio(file_path: str) -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    with open(file_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=f,
            response_format="text",
            language="en",          # locks to English, cuts most non-English hallucinations
        )

    transcript = result.strip() if result else ""

    # Empty
    if not transcript:
        return "__UNCLEAR__"

    # Single word or just punctuation — almost certainly noise
    if len(transcript.split()) <= 1:
        return "__UNCLEAR__"

    # Known hallucination phrase
    if transcript.lower().rstrip(".,!?") in _KNOWN_HALLUCINATIONS:
        return "__UNCLEAR__"

    return transcript
