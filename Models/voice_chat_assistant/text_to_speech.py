from gtts import gTTS
import uuid
import os

def text_to_speech(text: str, lang: str) -> str:
    os.makedirs("static/voice", exist_ok=True)

    filename = f"static/voice/{uuid.uuid4().hex}.mp3"
    lang_lower = lang.lower()

    if lang_lower == "hindi":
        lang_code = "hi"
    elif lang_lower == "hinglish":
        lang_code = "en"  # English TTS but Hinglish words — correct
    else:
        lang_code = "en"

    tts = gTTS(text=text, lang=lang_code)
    tts.save(filename)

    return filename
