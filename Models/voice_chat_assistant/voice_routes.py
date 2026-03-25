from fastapi import APIRouter, UploadFile, Form
import os
import tempfile

from deep_translator import GoogleTranslator
from speech_to_text import speech_to_text
from app import answer_user_query, collection   

router = APIRouter()


def _translate_to_english(text: str, source_lang: str) -> str:
    """
    Translate non-English transcriptions to English for better
    vector-similarity matching against English ChromaDB content.
    Returns original text if already English or translation fails.
    """
    lang = source_lang.lower()
    if lang == "english" or lang == "hinglish":
        # English is already English; Hinglish STT now outputs Latin script → good enough
        return text
    try:
        src_code = "hi" if lang == "hindi" else "auto"
        translated = GoogleTranslator(source=src_code, target="en").translate(text)
        print(f"[DEBUG] Translated query: '{text}' → '{translated}'")
        return translated if translated else text
    except Exception as e:
        print(f"[WARN] Translation failed, using original: {e}")
        return text


@router.post("/voice-chat")
async def voice_chat(file: UploadFile, language: str = Form("english")):
    temp_path = None
    try:
        # 1) Save uploaded audio to a temp file (STT requires a file path)
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".wav"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_path = tmp.name
        tmp.write(await file.read())
        tmp.close()

        # 2) Convert speech → text (in the user's language)
        user_msg = speech_to_text(temp_path, language)

        if not user_msg or user_msg.strip() == "":
            return {
                "audio_content_type": None,
                "reply": None,
                "transcription": None,
                "error": "Unable to understand voice message. Please speak clearly and try again."
            }

        # 3) Translate to English for accurate RAG retrieval
        #    (ChromaDB content is in English, so English queries match best)
        english_query = _translate_to_english(user_msg, language)

        # 4) Pass ENGLISH query to RAG — but language param ensures LLM responds in target language
        bot_reply = answer_user_query(english_query, collection, language)

        return {
            "audio_content_type": "audio/mpeg",
            "reply": bot_reply,
            "transcription": user_msg
        }

    except Exception as e:
        print(f"Voice chat error: {e}")
        return {
            "audio_content_type": None,
            "reply": None,
            "transcription": None,
            "error": f"Error processing voice message: {str(e)}"
        }

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
