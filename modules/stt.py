import whisper

model = None

def load_model():
    global model
    if model is None:
        model = whisper.load_model("base")

def transcribe_audio(file_path):
    load_model()
    result = model.transcribe(file_path)
    return result["text"]