from fastapi import APIRouter, UploadFile, Form
import os

from speech_to_text import speech_to_text
from text_to_speech import text_to_speech
from app import answer_user_query, collection   

router = APIRouter()

@router.post("/voice-chat")
async def voice_chat(file: UploadFile, language: str = Form("english")):
    temp_path = None
    try:
        # 1) Save uploaded audio temporarily
        os.makedirs("static/voice", exist_ok=True)
        temp_path = f"static/voice/{file.filename}"
        
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        # 2) Convert speech → text
        user_msg = speech_to_text(temp_path)

        if not user_msg or user_msg.strip() == "":
            return {
                "audio_url": None,
                "reply": None,
                "error": "Unable to understand voice message. Please speak clearly and try again."
            }

        # 3) Pass transcription to RAG — forced to selected language
        bot_reply = answer_user_query(user_msg, collection, language)

        # 4) Convert reply to speech — same language user selected
        audio_file = text_to_speech(bot_reply, language)

        return {
            "audio_url": audio_file,
            "reply": bot_reply,
            "transcription": user_msg
        }

    except Exception as e:
        print(f"Voice chat error: {e}")
        return {
            "audio_url": None,
            "reply": None,
            "error": f"Error processing voice message: {str(e)}"
        }

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
