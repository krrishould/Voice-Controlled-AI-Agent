import streamlit as st
import os
from modules.stt import transcribe_audio
from modules.intent import detect_intent
from modules.tools import execute_tool
from streamlit_mic_recorder import mic_recorder

st.set_page_config(page_title="Voice AI Agent", layout="centered")
st.title("Voice-Controlled AI Agent")

file_path = None

# -------- AUDIO INPUT --------
col1, col2 = st.columns(2)

with col1:
    st.subheader("Upload Audio")
    uploaded_file = st.file_uploader("Upload .wav or .mp3", type=["wav", "mp3"])
    if uploaded_file is not None:
        st.audio(uploaded_file)
        os.makedirs("output", exist_ok=True)
        file_path = os.path.join("output", uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

with col2:
    st.subheader("Record from Mic")
    audio = mic_recorder(start_prompt="Start recording", stop_prompt="Stop recording", key="mic")
    if audio:
        st.audio(audio["bytes"], format="audio/wav")
        os.makedirs("output", exist_ok=True)
        file_path = "output/recorded_audio.wav"
        with open(file_path, "wb") as f:
            f.write(audio["bytes"])

st.divider()

# -------- RUN PIPELINE --------
if file_path and st.button("Run Agent", type="primary", use_container_width=True):

    # Step 1: Transcribe
    with st.spinner("Transcribing audio..."):
        transcript = transcribe_audio(file_path)

    st.subheader("1. Transcription")
    st.info(transcript)

    # Step 2: Detect Intent
    with st.spinner("Detecting intent..."):
        intent_data = detect_intent(transcript)

    st.subheader("2. Detected Intent")
    intent_label = intent_data.get("intent", "unknown").replace("_", " ").title()
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.success(f"**{intent_label}**")
    with col_b:
        if intent_data.get("filename"):
            st.write(f"Target file: `{intent_data['filename']}`")
        if intent_data.get("description"):
            st.caption(intent_data["description"])

    # Step 3: Execute Tool
    with st.spinner("Executing action..."):
        result = execute_tool(intent_data, transcript)

    st.subheader("3. Action Taken")
    st.write(result["action"])
    if result.get("file_path"):
        st.caption(f"Saved to: `{result['file_path']}`")

    # Step 4: Output
    st.subheader("4. Output")
    if intent_data.get("intent") == "write_code":
        st.code(result["output"])
    else:
        st.write(result["output"])
