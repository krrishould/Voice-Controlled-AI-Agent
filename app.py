import streamlit as st
import os
from modules.stt import transcribe_audio

st.title("🎤 Voice-Controlled AI Agent")

uploaded_file = st.file_uploader("Upload an audio file", type=["wav", "mp3"])

if uploaded_file is not None:
    st.audio(uploaded_file)

    os.makedirs("output", exist_ok=True)
    file_path = os.path.join("output", uploaded_file.name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success("File saved!")

if uploaded_file.size == 0:
    st.error("Uploaded file is empty!")
    st.stop()

    #transcription 
    if st.button("Transcribe Audio"):
        text = transcribe_audio(file_path)

        st.subheader("Transcribed Text:")
        st.write(text)