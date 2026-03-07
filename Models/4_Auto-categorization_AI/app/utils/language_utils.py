from langdetect import detect
from deep_translator import GoogleTranslator


def detect_language(text: str) -> str:
    try:
        lang = detect(text)
        return lang
    except Exception:
        return "unknown"


def translate_to_english(text: str) -> str:

    lang = detect_language(text)

    if lang == "en":
        return text

    try:
        translated = GoogleTranslator(source="auto", target="en").translate(text)
        return translated
    except Exception:
        return text