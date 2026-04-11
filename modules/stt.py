from faster_whisper import WhisperModel

# Model is downloaded once from HuggingFace and cached locally after that.
# "base" is the sweet spot for CPU — fast enough, accurate enough.
# Change to "small" or "medium" if you want better accuracy (slower).
_MODEL = None

def _get_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = WhisperModel("base", device="cpu", compute_type="int8")
    return _MODEL


# Phrases faster-whisper/Whisper commonly hallucinates on silence or noise
_KNOWN_HALLUCINATIONS = {
    "thank you", "thanks for watching", "thank you for watching",
    "продолжение следует", "to be continued", "subtitles by",
    "subscribe", "please subscribe", "like and subscribe",
    "you", "bye", "okay", "ok", "hmm", "um", "uh",
    ".", "..", "...",
}


def transcribe_audio(file_path: str) -> str:
    model = _get_model()

    segments, info = model.transcribe(
        file_path,
        language="en",          # lock to English — cuts non-English hallucinations
        vad_filter=True,        # Voice Activity Detection: skips silent sections automatically
        vad_parameters=dict(
            min_silence_duration_ms=500,   # treat 500ms+ silence as a gap
        ),
    )

    transcript = " ".join(seg.text.strip() for seg in segments).strip()

    # Empty after VAD filtered out silence
    if not transcript:
        return "__UNCLEAR__"

    # Single word / punctuation only — almost certainly noise
    if len(transcript.split()) <= 1:
        return "__UNCLEAR__"

    # Known hallucination phrase
    if transcript.lower().rstrip(".,!?") in _KNOWN_HALLUCINATIONS:
        return "__UNCLEAR__"

    return transcript
