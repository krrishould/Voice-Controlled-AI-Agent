import streamlit as st
import os
from modules.stt import transcribe_audio
from modules.intent import detect_intent
from modules.tools import execute_tool
from streamlit_mic_recorder import mic_recorder

st.set_page_config(
    page_title="Voice AI Agent",
    page_icon="🎙️",
    layout="centered"
)

for key in ["file_path", "transcribed_text", "intent_data", "execution_result"]:
    if key not in st.session_state:
        st.session_state[key] = None

if "history" not in st.session_state:
    st.session_state.history = []

if "context_text" not in st.session_state:
    st.session_state.context_text = ""

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []


# ── Header ──────────────────────────────────────────────────────────────────────
st.markdown("# 🎙️ Voice AI Agent")
st.caption("Speak or upload audio — the agent transcribes it, understands your intent, and acts on it.")
st.divider()

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.markdown("#### Upload Audio")
        
        uploaded_file = st.file_uploader(
            "Upload audio file",            
            type=["wav", "mp3"],
            label_visibility="collapsed",   # ← hides label text visually, no layout glitch
            key="audio_uploader"
        )
        if uploaded_file:
            st.audio(uploaded_file)
            os.makedirs("output", exist_ok=True)
            fp = os.path.join("output", uploaded_file.name)
            with open(fp, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.session_state.file_path = fp

with col2:
    with st.container(border=True):
        st.markdown("#### Record from Mic")
        audio = mic_recorder(
            start_prompt="⏺  Start Recording",
            stop_prompt="⏹  Stop Recording",
            key="mic"
        )
        if audio:
            st.audio(audio["bytes"], format="audio/wav")
            os.makedirs("output", exist_ok=True)
            fp = "output/recorded_audio.wav"
            with open(fp, "wb") as f:
                f.write(audio["bytes"])
            st.session_state.file_path = fp

st.divider()

# ── Context Text Input ───────────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown("#### Text / Content Input")
    st.caption("Paste or type text here — the agent will use this as the content to act on (e.g. summarize, answer questions about it).")

    text_input_col, file_input_col = st.columns([2, 1])

    with text_input_col:
        typed_text = st.text_area(
            "Type or paste content",
            value=st.session_state.context_text,
            height=120,
            placeholder="Paste an article, code snippet, or any text you want the agent to work with...",
            label_visibility="collapsed",
        )
        st.session_state.context_text = typed_text

    with file_input_col:
        text_file = st.file_uploader(
            "Or upload a .txt file",
            type=["txt"],
            key="text_file_uploader",
        )
        if text_file:
            file_content = text_file.read().decode("utf-8")
            st.session_state.context_text = file_content
            st.success(f"Loaded: {text_file.name}")

st.divider()


# ── Pipeline ────────────────────────────────────────────────────────────────────
INTENT_ICONS = {
    "create_file":  "📄",
    "write_code":   "💻",
    "summarize":    "📝",
    "general_chat": "💬",
}

if not st.session_state.file_path:
    st.markdown(
        "<p style='text-align:center;color:#2A2A42;font-size:0.9rem;'>"
        "Provide audio above to get started."
        "</p>",
        unsafe_allow_html=True
    )
else:
    bcol1, bcol2 = st.columns([3, 1])
    with bcol1:
        run = st.button("▶  Run Agent", type="primary", use_container_width=True)
    with bcol2:
        # Reset clears all state and forces a fresh rerun
        if st.button("↺  Reset", use_container_width=True):
            for key in ["file_path", "transcribed_text", "intent_data", "execution_result"]:
                st.session_state[key] = None
            st.session_state.history = []
            st.session_state.chat_messages = []
            st.rerun()

    if run:
        # ── 01 Transcribe ───────────────────────────────────────────────────────
        with st.spinner("Transcribing..."):
            transcript = transcribe_audio(st.session_state.file_path)

        if transcript == "__UNCLEAR__":
            st.warning("Couldn't hear that clearly. Please try again with clearer audio.")
            st.stop()

        st.session_state.transcribed_text = transcript

        # ── 02 Intent ──────────────────────────────────────────────────────────
        with st.spinner("Detecting intent..."):
            intent_data = detect_intent(transcript)
            st.session_state.intent_data = intent_data

        # ── 03 Execute ─────────────────────────────────────────────────────────
        with st.spinner("Executing action..."):
            result = execute_tool(
                intent_data,
                transcript,
                st.session_state.context_text,
                st.session_state.chat_messages,
            )
            st.session_state.execution_result = result

            # Build the user message that was sent (command + any pasted context)
            user_msg = transcript
            if st.session_state.context_text.strip():
                user_msg += f"\n\nContext:\n{st.session_state.context_text.strip()}"

            # Append this turn to the running conversation history for the LLM
            st.session_state.chat_messages.append({"role": "user",      "content": user_msg})
            st.session_state.chat_messages.append({"role": "assistant", "content": result.get("output", "")})

            # Sidebar history entry
            st.session_state.history.append({
                "transcription": transcript,
                "intent": intent_data.get("intent", "unknown"),
                "action": result.get("action", ""),
                "output": result.get("output", ""),
                "success": True,
            })

# ── Results ─────────────────────────────────────────────────────────────────────
if st.session_state.transcribed_text:
    st.divider()

    intent_data   = st.session_state.intent_data   or {}
    result        = st.session_state.execution_result or {}
    intent_key    = intent_data.get("intent", "general_chat")
    intent_label  = intent_key.replace("_", " ").title()
    icon          = INTENT_ICONS.get(intent_key, "🤖")

    # 01 Transcript
    with st.container(border=True):
        st.markdown("#### 01 — Transcription")
        st.write(st.session_state.transcribed_text)

    # 02 Intent
    with st.container(border=True):
        st.markdown("#### 02 — Detected Intent")
        ca, cb = st.columns([1, 2])
        with ca:
            st.success(f"{icon}  {intent_label}")
        with cb:
            if intent_data.get("filename"):
                st.markdown(f"**File:** `{intent_data['filename']}`")
            if intent_data.get("content_hint"):
                st.caption(intent_data["content_hint"])

    # 03 Action
    with st.container(border=True):
        st.markdown("#### 03 — Action Taken")
        st.write(result.get("action", "—"))
        if result.get("file_path"):
            st.caption(f"Saved → `{result['file_path']}`")

    # 04 Output
    with st.container(border=True):
        st.markdown("#### 04 — Output")
        if intent_key == "write_code":
            lang = intent_data.get("language", "python")
            st.code(result.get("output", ""), language=lang)
        else:
            st.write(result.get("output", "—"))

        # Download button for any generated file
        fp = result.get("file_path")
        if fp and os.path.exists(fp):
            with open(fp, "r") as f:
                st.download_button(
                    f"⬇️  Download {os.path.basename(fp)}",
                    data=f.read(),
                    file_name=os.path.basename(fp),
                    mime="text/plain"
                )

# ── Session History (Sidebar) ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🕐 Session History")
    if len(st.session_state.history) == 0:
        st.caption("No commands yet. Run the agent to see history here.")
    else:
        st.caption(f"{len(st.session_state.history)} command(s) this session")
        for i, entry in enumerate(reversed(st.session_state.history), 1):
            status = "✅" if entry["success"] else "❌"
            with st.container(border=True):
                st.markdown(f"**{i}. {status} [{entry['intent'].replace('_', ' ').title()}]**")
                st.caption(f"_{entry['transcription']}_")
                st.caption(f"Action: {entry['action']}")