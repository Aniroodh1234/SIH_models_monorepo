from gtts import gTTS
import io
import os
import uuid

# ---------------------------------------------------------------------------
# Maximum number of MP3 files kept in the voice output directory at one time.
# When this limit is breached the oldest file(s) are deleted automatically.
# ---------------------------------------------------------------------------
VOICE_FILE_THRESHOLD = 3


def _get_lang_code(lang: str) -> str:
    """Map UI language name → gTTS language code."""
    lang_lower = lang.lower()
    if lang_lower == "hindi":
        return "hi"
    elif lang_lower == "hinglish":
        return "en"   # Hindi words in English letters — English TTS is correct
    elif lang_lower == "odia":
        return "or"   # Odia language code
    else:
        return "en"


def text_to_speech(text: str, lang: str) -> io.BytesIO:
    """
    Convert text to speech and return as an in-memory BytesIO buffer (MP3).
    No files are written to disk.
    (Original function — kept intact for any internal use.)
    """
    buffer = io.BytesIO()
    lang_code = _get_lang_code(lang)
    tts = gTTS(text=text, lang=lang_code)
    tts.write_to_fp(buffer)
    buffer.seek(0)
    return buffer


def text_to_speech_file(text: str, lang: str, voice_dir: str) -> str:
    """
    Convert text to speech and save it as an MP3 file inside *voice_dir*.

    Threshold enforcement (VOICE_FILE_THRESHOLD = 3):
      After saving, if the number of .mp3 files in *voice_dir* exceeds the
      threshold, the oldest file(s) — determined by modification time — are
      deleted until the count is at or below the threshold.

    Returns:
        The filename of the newly saved MP3 (e.g. "voice_a1b2c3d4.mp3").
    """
    # Ensure the target directory exists
    os.makedirs(voice_dir, exist_ok=True)

    # Generate a unique filename
    filename = f"voice_{uuid.uuid4().hex[:8]}.mp3"
    filepath = os.path.join(voice_dir, filename)

    # Generate TTS audio and write directly to the file
    lang_code = _get_lang_code(lang)
    tts = gTTS(text=text, lang=lang_code)
    tts.save(filepath)
    print(f"[TTS] Saved audio → {filepath}")

    # ---- Threshold cleanup ------------------------------------------------
    mp3_files = sorted(
        [
            os.path.join(voice_dir, f)
            for f in os.listdir(voice_dir)
            if f.lower().endswith(".mp3")
        ],
        key=os.path.getmtime   # oldest first
    )

    while len(mp3_files) > VOICE_FILE_THRESHOLD:
        oldest = mp3_files.pop(0)
        try:
            os.remove(oldest)
            print(f"[TTS] Threshold cleanup — deleted old file: {oldest}")
        except OSError as e:
            print(f"[TTS] Could not delete {oldest}: {e}")
    # -----------------------------------------------------------------------

    return filename
