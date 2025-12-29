import speech_recognition as sr
from pydub import AudioSegment
import os

# Set FFmpeg path explicitly for Windows if not in PATH
# Adjust this path to where your FFmpeg is installed
if os.name == 'nt':  # Windows
    possible_paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"D:\ffmpeg\bin\ffmpeg.exe"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            AudioSegment.converter = path
            print(f"[DEBUG] Using FFmpeg from: {path}")
            break


def speech_to_text(audio_path: str, ui_language: str = "english") -> str:
    """
    Convert any supported audio file (mp3, m4a, wav, ogg, webm…) to text.

    ui_language is the *target interface language* from the client:
    - "english"  -> use Google STT with en-IN
    - "hindi", "hinglish", "odia" -> use Google STT with hi-IN
    This keeps behaviour aligned with your text RAG pipeline.
    """
    print(f"[DEBUG] Processing audio file: {audio_path}")
    print(f"[DEBUG] File exists: {os.path.exists(audio_path)}")
    print(f"[DEBUG] File size: {os.path.getsize(audio_path) if os.path.exists(audio_path) else 0} bytes")
    
    # Convert any audio format to WAV
    wav_path = audio_path.rsplit('.', 1)[0] + '_converted.wav'
    
    try:
        # Detect file format and convert to WAV
        file_ext = audio_path.split('.')[-1].lower()
        print(f"[DEBUG] Detected format: {file_ext}")
        
        # Load audio file based on extension
        if file_ext == 'mp3':
            audio = AudioSegment.from_mp3(audio_path)
        elif file_ext == 'm4a':
            audio = AudioSegment.from_file(audio_path, format='m4a')
        elif file_ext == 'ogg':
            audio = AudioSegment.from_ogg(audio_path)
        elif file_ext == 'webm':
            audio = AudioSegment.from_file(audio_path, format='webm')
        elif file_ext == 'wav':
            audio = AudioSegment.from_wav(audio_path)
        else:
            # Try to load with automatic format detection
            audio = AudioSegment.from_file(audio_path)
        
        # Convert to mono and set sample rate for better recognition
        audio = audio.set_channels(1)       # Mono
        audio = audio.set_frame_rate(16000) # 16kHz
        
        # Export as WAV
        audio.export(wav_path, format='wav')
        print(f"[DEBUG] Conversion successful")
        print(f"[DEBUG] Converted file size: {os.path.getsize(wav_path)} bytes")
        print(f"[DEBUG] Audio duration: {len(audio) / 1000.0} seconds")
        
        # Now recognize the converted WAV file
        recognizer = sr.Recognizer()
        
        # Adjust recognizer settings for better accuracy
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        
        with sr.AudioFile(wav_path) as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)
            print(f"[DEBUG] Audio recorded, attempting recognition...")

        # -------- LANGUAGE-SELECTION FIX --------
        ui_lang = (ui_language or "english").lower()

        if ui_lang == "english":
            google_lang = "en-IN"     # or "en-US" if you prefer
        elif ui_lang in ("hindi", "hinglish", "odia"):
            google_lang = "hi-IN"     # Hindi locale, handles Hinglish pretty well
        else:
            google_lang = "hi-IN"

        print(f"[DEBUG] Using Google STT language: {google_lang}")
        text = recognizer.recognize_google(audio_data, language=google_lang)
        print(f"[DEBUG] Recognition successful: '{text}'")
        # ----------------------------------------
        
        # Clean up converted file
        if os.path.exists(wav_path):
            os.remove(wav_path)
            
        return text
        
    except sr.UnknownValueError:
        print("[ERROR] Google Speech Recognition could not understand audio")
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except:
                pass
        return ""
        
    except sr.RequestError as e:
        print(f"[ERROR] Could not request results from Google Speech Recognition; {e}")
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except:
                pass
        return ""
        
    except Exception as e:
        print(f"[ERROR] Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except:
                pass
        return ""
