import streamlit as st
import os

st.title("🎤 Voice-Controlled AI Agent")

# Upload audio file
uploaded_file = st.file_uploader("Upload an audio file", type=["wav", "mp3"])

if uploaded_file is not None:
    st.audio(uploaded_file)

    # Create output folder
    os.makedirs("output", exist_ok=True)

    file_path = os.path.join("output", uploaded_file.name)

    # Save file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success(f"Saved to {file_path}")