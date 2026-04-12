import streamlit as st
import os
from modules.stt import transcribe_audio
from modules.intent import detect_intent
from modules.tools import execute_tool
from streamlit_mic_recorder import mic_recorder

st.set_page_config(
    page_title="Voice AI Agent",
    page_icon="🎙️",
    layout="wide",
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .stButton > button { border-radius: 8px; }
    [data-testid="stSidebarContent"] { padding-top: 1.5rem; }
    .step-label { font-size: 0.75rem; font-weight: 600; letter-spacing: 0.08em;
                  text-transform: uppercase; color: #888; margin-bottom: 0.25rem; }
</style>
""", unsafe_allow_html=True)

# ── Session State ────────────────────────────────────────────────────────────────
for key in ["file_path", "transcribed_text", "intent_data", "execution_result"]:
    if key not in st.session_state:
        st.session_state[key] = None

if "history" not in st.session_state:
    st.session_state.history = []

if "context_text" not in st.session_state:
    st.session_state.context_text = ""

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# ── Sidebar ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎙️ Voice AI Agent")
    st.divider()

    c1, c2 = st.columns(2)
    c1.metric("Commands", len(st.session_state.history))
    c2.metric("Memory turns", len(st.session_state.chat_messages) // 2)

    if st.button("🗑️  Clear Session", use_container_width=True):
        for key in ["file_path", "transcribed_text", "intent_data", "execution_result"]:
            st.session_state[key] = None
        st.session_state.history = []
        st.session_state.chat_messages = []
        st.session_state.context_text = ""
        st.rerun()

    st.divider()
    st.markdown("#### Session History")

    if not st.session_state.history:
        st.caption("No commands yet. Run the agent to see history here.")
    else:
        INTENT_ICONS = {
            "create_file":  "📄",
            "write_code":   "💻",
            "summarize":    "📝",
            "general_chat": "💬",
        }
        for i, entry in enumerate(reversed(st.session_state.history), 1):
            icon = INTENT_ICONS.get(entry["intent"], "🤖")
            label = entry["intent"].replace("_", " ").title()
            with st.container(border=True):
                st.markdown(f"**{i}. {icon} {label}**")
                transcript_preview = entry["transcription"]
                if len(transcript_preview) > 70:
                    transcript_preview = transcript_preview[:70] + "…"
                st.caption(f"_{transcript_preview}_")

# ── Main Layout ──────────────────────────────────────────────────────────────────
st.markdown("# 🎙️ Voice AI Agent")
st.caption("Record or upload audio — the agent transcribes it, detects intent, and acts.")
st.divider()

# ── Input Row ────────────────────────────────────────────────────────────────────
input_col1, input_col2, input_col3 = st.columns([1, 1, 1.2])

with input_col1:
    with st.container(border=True):
        st.markdown("#### 🎤 Record from Mic")
        audio = mic_recorder(
            start_prompt="⏺  Start Recording",
            stop_prompt="⏹  Stop Recording",
            key="mic",
        )
        if audio:
            st.audio(audio["bytes"], format="audio/wav")
            os.makedirs("output", exist_ok=True)
            with open("output/recorded_audio.wav", "wb") as f:
                f.write(audio["bytes"])
            st.session_state.file_path = "output/recorded_audio.wav"

with input_col2:
    with st.container(border=True):
        st.markdown("#### 📁 Upload Audio")
        uploaded_file = st.file_uploader(
            "Upload audio file",
            type=["wav", "mp3"],
            label_visibility="collapsed",
            key="audio_uploader",
        )
        if uploaded_file:
            st.audio(uploaded_file)
            os.makedirs("output", exist_ok=True)
            fp = os.path.join("output", uploaded_file.name)
            with open(fp, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.session_state.file_path = fp

with input_col3:
    with st.container(border=True):
        st.markdown("#### 📄 Content Input *(optional)*")
        st.caption("Paste text for the agent to work on — summarize, answer questions, etc.")

        typed = st.text_area(
            "content",
            value=st.session_state.context_text,
            height=95,
            placeholder="Paste an article, notes, or any text here…",
            label_visibility="collapsed",
        )
        st.session_state.context_text = typed

        txt_file = st.file_uploader("Or upload a .txt", type=["txt"], key="txt_uploader")
        if txt_file:
            st.session_state.context_text = txt_file.read().decode("utf-8")
            st.rerun()

st.divider()

# ── Run / Reset ──────────────────────────────────────────────────────────────────
INTENT_ICONS = {
    "create_file":  "📄",
    "write_code":   "💻",
    "summarize":    "📝",
    "general_chat": "💬",
}

if not st.session_state.file_path:
    st.info("Provide audio via mic or upload above to get started.", icon="👆")
else:
    btn_col, reset_col = st.columns([5, 1])
    with btn_col:
        run = st.button("▶  Run Agent", type="primary", use_container_width=True)
    with reset_col:
        if st.button("↺  Reset", use_container_width=True):
            for key in ["file_path", "transcribed_text", "intent_data", "execution_result"]:
                st.session_state[key] = None
            st.rerun()

    if run:
        with st.spinner("Transcribing…"):
            transcript = transcribe_audio(st.session_state.file_path)

        if transcript == "__UNCLEAR__":
            st.warning("Couldn't hear that clearly — please try again with clearer audio.")
            st.stop()

        st.session_state.transcribed_text = transcript

        with st.spinner("Detecting intent…"):
            intent_data = detect_intent(transcript)
            st.session_state.intent_data = intent_data

        with st.spinner("Executing action…"):
            result = execute_tool(
                intent_data,
                transcript,
                st.session_state.context_text,
                st.session_state.chat_messages,
            )
            st.session_state.execution_result = result

            # Append this turn to conversational memory
            user_msg = transcript
            if st.session_state.context_text.strip():
                user_msg += f"\n\nContext:\n{st.session_state.context_text.strip()}"
            st.session_state.chat_messages.append({"role": "user",      "content": user_msg})
            st.session_state.chat_messages.append({"role": "assistant", "content": result.get("output", "")})

            st.session_state.history.append({
                "transcription": transcript,
                "intent":  intent_data.get("intent", "unknown"),
                "action":  result.get("action", ""),
                "output":  result.get("output", ""),
                "success": True,
            })

# ── Results ──────────────────────────────────────────────────────────────────────
if st.session_state.transcribed_text:
    st.divider()

    intent_data  = st.session_state.intent_data  or {}
    result       = st.session_state.execution_result or {}
    intent_key   = intent_data.get("intent", "general_chat")
    intent_label = intent_key.replace("_", " ").title()
    icon         = INTENT_ICONS.get(intent_key, "🤖")

    top_left, top_right = st.columns(2)

    with top_left:
        with st.container(border=True):
            st.markdown('<p class="step-label">01 — Transcription</p>', unsafe_allow_html=True)
            st.write(st.session_state.transcribed_text)

    with top_right:
        with st.container(border=True):
            st.markdown('<p class="step-label">02 — Detected Intent</p>', unsafe_allow_html=True)
            st.success(f"{icon}  {intent_label}")
            if intent_data.get("filename"):
                st.caption(f"File: `{intent_data['filename']}`")
            if intent_data.get("content_hint"):
                st.caption(intent_data["content_hint"])

    with st.container(border=True):
        st.markdown('<p class="step-label">03 — Action Taken</p>', unsafe_allow_html=True)
        st.write(result.get("action", "—"))
        if result.get("file_path"):
            st.caption(f"Saved → `{result['file_path']}`")

    with st.container(border=True):
        st.markdown('<p class="step-label">04 — Output</p>', unsafe_allow_html=True)
        if intent_key == "write_code":
            lang = intent_data.get("language", "python")
            st.code(result.get("output", ""), language=lang)
        else:
            st.write(result.get("output", "—"))

        fp = result.get("file_path")
        if fp and os.path.exists(fp):
            with open(fp, "r") as f:
                st.download_button(
                    f"⬇️  Download {os.path.basename(fp)}",
                    data=f.read(),
                    file_name=os.path.basename(fp),
                    mime="text/plain",
                )
