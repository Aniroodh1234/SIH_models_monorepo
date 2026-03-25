from gtts import gTTS
import io

def text_to_speech(text: str, lang: str) -> io.BytesIO:
    """
    Convert text to speech and return as an in-memory BytesIO buffer (MP3).
    No files are written to disk.
    """
    buffer = io.BytesIO()
    lang_lower = lang.lower()

    if lang_lower == "hindi":
        lang_code = "hi"
    elif lang_lower == "hinglish":
        lang_code = "en"  # English TTS but Hinglish words — correct
    elif lang_lower == "odia":
        lang_code = "or"  # Odia language code
    else:
        lang_code = "en"

    tts = gTTS(text=text, lang=lang_code)
    tts.write_to_fp(buffer)
    buffer.seek(0)

    return buffer
