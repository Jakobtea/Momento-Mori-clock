import streamlit as st
import sounddevice as sd
from scipy.io.wavfile import write
import whisper
import numpy as np
import tempfile
import os

st.set_page_config(page_title="Speech to Text", page_icon="🎙️", layout="centered")
st.title("🎙️ Speech-to-Text (Start / Stop)")
st.markdown("Press **Start Recording**, speak, then press **Stop Recording**.")

# --- Config ---
SR = 44100  # sample rate

# --- initialize session_state keys ---
if "recording" not in st.session_state:
    st.session_state.recording = False
if "frames" not in st.session_state:
    st.session_state.frames = []
if "stream" not in st.session_state:
    st.session_state.stream = None
if "status_msg" not in st.session_state:
    st.session_state.status_msg = ""

# --- callback for InputStream ---
def audio_callback(indata, frames, time_info, status):
    if status:
        st.session_state.status_msg = str(status)
    st.session_state.frames.append(indata.copy())

# --- UI Buttons ---
col1, col2 = st.columns(2)
start_clicked = col1.button("🎧 Start Recording")
stop_clicked  = col2.button("⏹️ Stop Recording")

# --- Start recording ---
if start_clicked and not st.session_state.recording:
    st.session_state.frames = []
    try:
        st.session_state.stream = sd.InputStream(
            samplerate=SR,
            channels=1,
            dtype="float32",
            callback=audio_callback
        )
        st.session_state.stream.start()
        st.session_state.recording = True
        st.success("🎙️ Recording started")
    except Exception as e:
        st.error(f"Could not start audio input: {e}")

# --- Stop recording and process ---
if stop_clicked and st.session_state.recording:
    try:
        st.session_state.stream.stop()
        st.session_state.stream.close()
    except Exception as e:
        st.warning(f"Error stopping stream: {e}")

    st.session_state.recording = False
    st.success("✅ Recording stopped")

    if len(st.session_state.frames) == 0:
        st.warning("No audio captured.")
    else:
        audio_np = np.concatenate(st.session_state.frames, axis=0)
        if audio_np.ndim > 1:
            audio_np = audio_np.reshape(-1)

        int16_audio = (audio_np * 32767).astype(np.int16)
        tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        write(tmpfile.name, SR, int16_audio)
        st.audio(tmpfile.name, format="audio/wav")

        st.write("🧠 Transcribing with Whisper...")
        model = whisper.load_model("base")
        result = model.transcribe(tmpfile.name)
        transcription = result.get("text", "")
        st.subheader("📝 Transcription")
        st.write(transcription)

        try:
            os.remove(tmpfile.name)
        except OSError:
            pass

st.write(f"**Status:** {'Recording...' if st.session_state.recording else 'Idle'}")
if st.session_state.status_msg:
    st.write(f"**Audio status:** {st.session_state.status_msg}")
