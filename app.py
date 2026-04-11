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

# ── Styles ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

/* Apply font globally */
html, body, [class*="st-"], .stMarkdown, button, input,
textarea, select, p, span, div, label {
    font-family: 'Space Grotesk', sans-serif !important;
}

/* Background */
.stApp {
    background-color: #09090F;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }

/* Content width & padding */
.block-container {
    padding-top: 3.5rem !important;
    padding-bottom: 3rem !important;
    max-width: 780px !important;
}

/* ── Typography ── */
h1 {
    color: #EEEEF5 !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.8px !important;
}

h4 {
    color: #55556A !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
}

p { color: #B0B0C8 !important; }

small, .stCaption > p {
    color: #55556A !important;
    font-size: 0.78rem !important;
}

/* ── Bordered containers ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #101018 !important;
    border: 1px solid #1C1C2E !important;
    border-radius: 14px !important;
    padding: 0.25rem 0.25rem !important;
}

/* ── Divider ── */
hr {
    border-color: #1C1C2E !important;
    margin: 1.5rem 0 !important;
}

/* ── Primary button (Run Agent only) ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366F1, #8B5CF6) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.03em !important;
    height: 2.8rem !important;
    transition: box-shadow 0.2s ease, opacity 0.2s ease !important;
}

.stButton > button[kind="primary"]:hover {
    opacity: 0.85 !important;
    box-shadow: 0 0 28px rgba(99, 102, 241, 0.45) !important;
}

/* ── Secondary / default button (mic recorder) ── */
.stButton > button[kind="secondary"] {
    background-color: #1C1C2E !important;
    border: 1px solid #2A2A40 !important;
    border-radius: 8px !important;
    color: #AAAACC !important;
    font-weight: 500 !important;
}

/* ── File uploader ── */
[data-testid="stFileUploaderDropzone"] {
    background-color: #0D0D1A !important;
    border: 1px dashed #2A2A40 !important;
    border-radius: 10px !important;
}

/* Kill the browser's native file-input button (the one causing the double text) */
[data-testid="stFileUploaderDropzone"] input[type="file"]::file-selector-button {
    display: none !important;
}
[data-testid="stFileUploaderDropzone"] input[type="file"]::-webkit-file-upload-button {
    display: none !important;
}
[data-testid="stFileUploaderDropzone"] input[type="file"] {
    color: transparent !important;
    font-size: 0 !important;
}

/* ── Hide heading anchor link icons ── */
h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
    display: none !important;
}

/* ── Info box (step 01 transcript) ── */
.stAlert[data-baseweb="notification"] {
    border-radius: 10px !important;
    border: 1px solid #1C1C2E !important;
    background-color: #101018 !important;
}

/* ── Success badge (intent) ── */
[data-testid="stNotificationContentSuccess"] {
    background-color: #0C1F18 !important;
    border: 1px solid #163326 !important;
    color: #34D399 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}

/* ── Code block ── */
.stCode, [data-testid="stCode"] {
    border-radius: 10px !important;
}

/* ── File uploader box ── */
[data-testid="stFileUploaderDropzone"] {
    background-color: #0D0D1A !important;
    border: 1px dashed #2A2A40 !important;
    border-radius: 10px !important;
}

[data-testid="stFileUploaderDropzoneInstructions"] p {
    color: #55556A !important;
}
</style>
""", unsafe_allow_html=True)


# ── Header ──────────────────────────────────────────────────────────────────────
st.markdown("# 🎙️ Voice AI Agent")
st.caption("Speak or upload audio — the agent transcribes it, understands your intent, and acts on it.")
st.divider()


# ── Audio Input ─────────────────────────────────────────────────────────────────
file_path = None
col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.markdown("#### Upload Audio")
        uploaded_file = st.file_uploader(
            "file", type=["wav", "mp3"], label_visibility="collapsed"
        )
        if uploaded_file:
            st.audio(uploaded_file)
            os.makedirs("output", exist_ok=True)
            file_path = os.path.join("output", uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

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
            file_path = "output/recorded_audio.wav"
            with open(file_path, "wb") as f:
                f.write(audio["bytes"])

st.divider()


# ── Pipeline ────────────────────────────────────────────────────────────────────
INTENT_ICONS = {
    "create_file":  "📄",
    "write_code":   "💻",
    "summarize":    "📝",
    "general_chat": "💬",
}

if not file_path:
    st.markdown(
        "<p style='text-align:center;color:#2A2A42;font-size:0.9rem;'>"
        "Provide audio above to get started."
        "</p>",
        unsafe_allow_html=True
    )
else:
    if st.button("▶  Run Agent", type="primary", use_container_width=True):

        # ── 01 Transcribe ───────────────────────────────────────────────────────
        with st.spinner("Transcribing..."):
            transcript = transcribe_audio(file_path)

        with st.container(border=True):
            st.markdown("#### 01 — Transcription")
            st.write(transcript)

        # ── 02 Intent ──────────────────────────────────────────────────────────
        with st.spinner("Detecting intent..."):
            intent_data = detect_intent(transcript)

        intent_key   = intent_data.get("intent", "general_chat")
        intent_label = intent_key.replace("_", " ").title()
        icon         = INTENT_ICONS.get(intent_key, "🤖")

        with st.container(border=True):
            st.markdown("#### 02 — Detected Intent")
            ca, cb = st.columns([1, 2])
            with ca:
                st.success(f"{icon}  {intent_label}")
            with cb:
                if intent_data.get("filename"):
                    st.markdown(f"**File:** `{intent_data['filename']}`")
                if intent_data.get("description"):
                    st.caption(intent_data["description"])

        # ── 03 Execute ─────────────────────────────────────────────────────────
        with st.spinner("Executing action..."):
            result = execute_tool(intent_data, transcript)

        with st.container(border=True):
            st.markdown("#### 03 — Action Taken")
            st.write(result["action"])
            if result.get("file_path"):
                st.caption(f"Saved → `{result['file_path']}`")

        # ── 04 Output ──────────────────────────────────────────────────────────
        with st.container(border=True):
            st.markdown("#### 04 — Output")
            if intent_key == "write_code":
                st.code(result["output"], language="python")
            else:
                st.write(result["output"])
