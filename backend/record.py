import os
import time
import threading
import logging
import wave
from datetime import datetime
from dotenv import load_dotenv
import sounddevice as sd
import numpy as np
import mss
import signal

# Load environment variables
load_dotenv()
SCREENSHOT_INTERVAL = int(os.getenv("SCREENSHOT_INTERVAL", 5))
AUDIO_DURATION = int(os.getenv("DEFAULT_AUDIO_DURATION", 10))  # seconds
OUTPUT_ROOT = os.path.abspath(os.getenv("OUTPUT_DIR", "../sessions"))

# Logging setup
LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "record.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

AUDIO_FS = 44100  # Sample rate

# Global flag for graceful termination
stop_flag = threading.Event()

def signal_handler(sig, frame):
    logging.info("🔴 Termination signal received. Stopping...")
    stop_flag.set()

signal.signal(signal.SIGINT, signal_handler)

def record_audio(output_file, duration=AUDIO_DURATION, samplerate=AUDIO_FS):
    try:
        input_device = sd.default.device[0]
        device_info = sd.query_devices(input_device, 'input')
        channels = device_info.get('max_input_channels', 1)
        if channels < 1 or channels > 2:
            logging.warning(f"Invalid number of input channels ({channels}); falling back to mono.")
            channels = 1

        logging.info(f"Recording audio with {channels} channel(s) from: {device_info.get('name', 'Unknown device')}")
        
        total_frames = int(duration * samplerate)
        audio = np.zeros((total_frames, channels), dtype='int16')
        stream = sd.InputStream(samplerate=samplerate, channels=channels, dtype='int16')

        with stream:
            recorded_frames = 0
            start_time = time.time()
            while time.time() - start_time < duration:
                if stop_flag.is_set():
                    logging.info("Stop flag detected during audio recording.")
                    break
                buffer, overflow = stream.read(samplerate // 5)
                if overflow:
                    logging.warning("Buffer overflow occurred during recording.")
                frames = len(buffer)
                end_frame = recorded_frames + frames
                if end_frame > total_frames:
                    end_frame = total_frames
                    frames = total_frames - recorded_frames
                audio[recorded_frames:end_frame] = buffer[:frames]
                recorded_frames += frames
            logging.info(f"Recorded {recorded_frames} frames out of {total_frames}")
            
        audio = audio[:recorded_frames]
        with wave.open(output_file, 'w') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(samplerate)
            wf.writeframes(audio.tobytes())
        logging.info(f"✅ Audio recording complete. Saved to: {output_file}")
        print(f"Audio saved to: {output_file}")
        if not os.path.exists(output_file):
            logging.error(f"Audio file was not created: {output_file}")
        else:
            logging.info(f"Audio file exists: {os.path.abspath(output_file)}")
    except Exception as e:
        logging.error(f"❌ Audio recording error: {e}", exc_info=True)

def capture_screen(session_dir):
    try:
        logging.info("Starting screenshot capture...")
        with mss.mss() as sct:
            count = 0
            start_time = time.time()
            while time.time() - start_time < AUDIO_DURATION:
                if stop_flag.is_set():
                    logging.info("Stop flag detected during screen capture.")
                    break
                filename = os.path.join(session_dir, f"screenshot_{count:03}.png")
                # Capture and save the screenshot
                sct.shot(output=filename)
                logging.info(f"📸 Saved screenshot: {filename}")
                print(f"Screenshot saved: {filename}")
                time.sleep(SCREENSHOT_INTERVAL)
                count += 1
        logging.info("✅ Screen capture complete.")
    except Exception as e:
        logging.error(f"❌ Screen capture error: {e}", exc_info=True)

def main():
    logging.info("🚀 Session started")
    print("Session started")
    
    # Create a new session directory for this recording session
    timestamp = datetime.now().strftime("session_%Y%m%d_%H%M%S")
    session_dir = os.path.join(OUTPUT_ROOT, timestamp)
    try:
        os.makedirs(session_dir, exist_ok=True)
        logging.info(f"Session directory created at: {session_dir}")
        print(f"Session directory created at: {session_dir}")
    except Exception as e:
        logging.error(f"Failed to create session directory: {e}")
        return  # Abort if session directory cannot be created
    
    # Create the audio file path inside the session directory
    audio_file = os.path.join(session_dir, "audio.wav")
    
    audio_thread = threading.Thread(target=record_audio, args=(audio_file,), name="AudioThread")
    screen_thread = threading.Thread(target=capture_screen, args=(session_dir,), name="ScreenThread")

    audio_thread.start()
    screen_thread.start()

    audio_thread.join()
    screen_thread.join()

    logging.info("✅ Session finished")
    print("✔️ Session complete. Files saved to:", session_dir)

if __name__ == '__main__':
    main()