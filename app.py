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
            result = execute_tool(intent_data, transcript)
            st.session_state.execution_result = result

            # Session memory (bonus feature)
            st.session_state.history.append({
                "transcription": transcript,
                "intent": intent_data.get("intent", "unknown"),
                "action": result.get("action", ""),
                "output": result.get("output", ""),
                "success": True,  # if we reach this line, execution succeeded
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

# ── Session History ──────────────────────────────────────────────────────────────
if len(st.session_state.history) > 0:
    st.divider()
    with st.expander(f"🕐 Session History  ({len(st.session_state.history)} commands)", expanded=False):
        for i, entry in enumerate(reversed(st.session_state.history), 1):
            status = "✅" if entry["success"] else "❌"
            st.markdown(f"**{i}. {status} [{entry['intent']}]** — _{entry['transcription']}_")
            st.caption(f"Action: {entry['action']}")
            st.divider()