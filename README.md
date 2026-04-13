# Voice Controlled AI Agent

A fully local-first, voice-driven AI agent built with Streamlit. Speak a command (or upload audio), and the agent transcribes it, understands your intent, and acts on it -- creating files, writing code, summarizing text, or answering questions -- all while remembering your conversation across the session.

---

## Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Hardware and API Workarounds](#hardware-and-api-workarounds)
5. [Setup Instructions](#setup-instructions)
6. [Running the App](#running-the-app)
7. [How to Use](#how-to-use)
8. [Environment Variables](#environment-variables)
9. [Dependencies](#dependencies)

---

## Features

- **Voice input** -- record directly from mic or upload a `.wav` / `.mp3` file
- **Text / file input** -- paste text or upload a `.txt` for the agent to work on
- **4 supported intents** -- Create File, Write Code, Summarize, General Chat
- **Conversational memory** -- the LLM remembers all prior turns in the session, so follow-up commands like "now put that in a file" work naturally
- **Session history** -- sidebar shows every command run in the current session with intent labels
- **Download outputs** -- any generated file (code, summary) can be downloaded directly from the UI

---

## Architecture

The pipeline has three stages. Each stage runs sequentially on every Run Agent click.

```
Audio Input (mic / upload)
        |
        v
+-------------------------+
|  01  TRANSCRIBE         |  Groq API  ->  whisper-large-v3
|  modules/stt.py         |  Converts audio bytes to a text transcript
+----------+--------------+
           |  transcript (string)
           v
+-------------------------+
|  02  INTENT DETECT      |  Local Ollama  ->  llama3.2
|  modules/intent.py      |  Classifies the command into one of 4 intents
+----------+--------------+
           |  intent_data { intent, filename, description }
           v
+-------------------------+
|  03  EXECUTE TOOL       |  Local Ollama  ->  llama3.2
|  modules/tools.py       |  Routes to the correct action, calls LLM with chat history
+----------+--------------+
           |  result { action, output, file_path }
           v
  Streamlit UI  ->  displays transcription, intent, action, output
                    appends turn to chat_messages (conversational memory)
```

### Intent Detection -- Hybrid Approach

`modules/intent.py` uses a two-pass system to keep latency low:

1. **Rule-based first** -- fast regex and keyword matching handles common patterns without
   touching the LLM (e.g. "create a file named...", "write python code to...", "summarize this").
2. **LLM fallback** -- if no rule matches, the transcript is sent to `llama3.2` via Ollama
   with a structured JSON prompt to classify intent.

### Conversational Memory

Every completed turn appends two entries to `st.session_state.chat_messages`:

```python
{"role": "user",      "content": transcript + optional context text}
{"role": "assistant", "content": LLM output}
```

This list is threaded into every Ollama call as message history, giving the model full context
of the session. **Clear Session** in the sidebar wipes it clean.

### Tool Routing

| Intent       | What it does                                                            |
|--------------|-------------------------------------------------------------------------|
| create_file  | Creates an empty file in `output/` -- no LLM call needed               |
| write_code   | Calls LLM with full chat history, saves generated code to `output/`    |
| summarize    | Summarizes the Content Input text if provided, otherwise the transcript |
| general_chat | Passes transcript + any context text to LLM with full chat history      |

---

## Project Structure

```
VoiceControlledAI/
|
+-- app.py                  # Streamlit UI -- layout, state, pipeline orchestration
|
+-- modules/
|   +-- stt.py              # Speech-to-text via Groq Whisper API
|   +-- intent.py           # Hybrid intent classifier (rule-based + LLM fallback)
|   +-- tools.py            # Tool executor -- routes intent to the correct action
|
+-- output/                 # All generated files land here (created at runtime)
|
+-- .env                    # API keys -- not committed to git
+-- requirements.txt        # Python dependencies
+-- README.md
```

---

## Hardware and API Workarounds

### Why Groq for transcription instead of local Whisper?

Running OpenAI Whisper locally requires a CUDA-capable GPU or significant CPU time
(30-60 seconds+ for a short clip on CPU-only hardware). To keep the pipeline fast on a regular
laptop, **Groq's hosted Whisper API** (`whisper-large-v3`) is used instead. It transcribes audio
in under 2 seconds and the free tier is generous enough for development.

**Tradeoff:** requires internet + a Groq API key. If you want a fully offline setup, replace
`modules/stt.py` with a local call using the `faster-whisper` package.

### Why Ollama for the LLM instead of an API?

Intent detection and all tool execution use **Ollama running locally** with `llama3.2`
(3B parameters). This means:

- No API key or cost for LLM calls
- Works fully offline after the model is pulled once
- `llama3.2` runs comfortably on CPU-only machines (4-8 GB RAM)

**Tradeoff:** the first response after a cold start can be slow (~5-10s on CPU). Subsequent
calls are faster as Ollama keeps the model loaded in memory.

### Why streamlit-mic-recorder for the microphone?

Direct microphone access via Python (`pyaudio`, `sounddevice`) requires native audio drivers
and often fails on Windows without extra setup -- PortAudio DLLs, build tools, etc.
`streamlit-mic-recorder` handles recording entirely in the **browser** using the Web Audio API
and sends the audio bytes back to Python as a WAV file. No OS-level audio driver configuration
needed.

---

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- [Ollama](https://ollama.com/download) installed and running
- A [Groq](https://console.groq.com/) account (free) for the Whisper API key

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd VoiceControlledAI
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
pip install ollama streamlit-mic-recorder
```

> **Note:** `ollama` and `streamlit-mic-recorder` are used by the app but not yet listed in
> `requirements.txt` -- install them with the second command above.

### 4. Pull the LLM model

Make sure Ollama is running, then pull the model used for intent detection and tool execution:

```bash
ollama pull llama3.2
```

Verify it downloaded correctly:

```bash
ollama list
```

### 5. Create your .env file

Create a file named `.env` in the project root:

```
GROQ_API_KEY=your_groq_api_key_here
```

Get a free key at [console.groq.com](https://console.groq.com) -> API Keys -> Create API Key.

---

## Running the App

Make sure Ollama is running in the background (it auto-starts after install on most systems),
then:

```bash
streamlit run app.py
```

The app opens in your browser at `http://localhost:8501`.

---

## How to Use

1. **Record or upload audio** -- use the mic recorder or upload a `.wav` / `.mp3` file
2. *(Optional)* **Paste content** -- if you want the agent to summarize or reason about a piece
   of text, paste it in the Content Input box on the right
3. **Click Run Agent** -- the pipeline runs and results appear below in four labeled steps
4. **Follow-up commands work** -- the agent remembers previous turns, for example:
   - "Tell me about neural networks" -> then -> "Now write that as a Python docstring"
   - "Summarize this" (with text pasted) -> then -> "Make it even shorter"
5. **Download outputs** -- any generated file has a download button in the Output section
6. **Clear Session** in the sidebar resets all memory and history for a fresh start

---

## Environment Variables

| Variable     | Required | Description                                        |
|--------------|----------|----------------------------------------------------|
| GROQ_API_KEY | Yes      | API key for Groq Whisper transcription             |

---

## Dependencies

| Package                | Version   | Purpose                                              |
|------------------------|-----------|------------------------------------------------------|
| streamlit              | >= 1.35.0 | Web UI framework                                     |
| groq                   | >= 0.9.0  | Groq API client for Whisper transcription            |
| ollama                 | >= 0.6.1  | Local LLM client (intent detection + tool execution) |
| streamlit-mic-recorder | >= 0.0.8  | Browser-based mic recording (no audio driver needed) |
| python-dotenv          | >= 1.0.0  | Loads .env file for API keys                         |
| pydub                  | >= 0.25.1 | Audio file handling                                  |
