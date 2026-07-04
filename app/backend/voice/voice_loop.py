import time

import sounddevice as sd

from app.backend.voice.wake_word import listen_for_wake_word as _listen_for_wake_word
from app.backend.voice.vad import is_speech, reset_vad, CHUNK_SIZE, SAMPLE_RATE
from app.backend.voice.stt import transcribe
from app.backend.voice.tts import synthesize

POST_TTS_COOLDOWN_SECONDS = 0.3  # let mic AGC settle after TTS playback

SILENCE_TIMEOUT_SECONDS = 10
RESUME_TIMER_AFTER_PAUSE_SECONDS = 4
MAX_UTTERANCE_SECONDS = 15  # safety cap on a single recording, prevents runaway listening


def speak(text: str) -> None:
    """Synthesize and immediately (blocking) play a line of text.

    After playback finishes, pauses briefly and resets the VAD model's
    internal state so that mic bleed / ambient noise right after TTS
    doesn't trigger a false speech detection.
    """
    audio, sample_rate = synthesize(text)
    sd.play(audio, sample_rate)
    sd.wait()
    time.sleep(POST_TTS_COOLDOWN_SECONDS)
    reset_vad()


def wait_for_wake_word() -> None:
    """Blocks until the wake word is detected."""
    _listen_for_wake_word()


def _listen_for_turn_or_sleep():
    """
    Single continuous stream that both waits for the next turn AND
    records it, with no handoff gap between detection and capture.

    - Silence timer: pauses while speech is happening, resumes counting
      RESUME_TIMER_AFTER_PAUSE_SECONDS (4s) after speech stops, then
      counts down SILENCE_TIMEOUT_SECONDS (10s) before giving up.
    - The instant speech is detected, recording begins in the SAME
      stream (no frames lost), and continues until 0.8s trailing
      silence or MAX_UTTERANCE_SECONDS is hit.

    Returns a list of recorded chunks if the user spoke, or None if
    the full silence timeout elapsed with nothing heard.
    """
    check_interval_frames = CHUNK_SIZE / SAMPLE_RATE  # seconds per frame read
    silence_since_last_speech = 0.0
    countdown_remaining = SILENCE_TIMEOUT_SECONDS
    countdown_running = False

    recording = False
    chunks = []
    silence_start = None
    recording_start_time = None

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
        while True:
            frame, _ = stream.read(CHUNK_SIZE)
            frame = frame.flatten()
            speech = is_speech(frame)

            if not recording:
                print(f"DEBUG: speech={speech} countdown_running={countdown_running} silence_since={silence_since_last_speech:.1f} countdown_remaining={countdown_remaining:.1f}")
                if speech:
                    recording = True
                    recording_start_time = time.time()
                    chunks.append(frame)
                    continue

                if not countdown_running:
                    silence_since_last_speech += check_interval_frames
                    if silence_since_last_speech >= RESUME_TIMER_AFTER_PAUSE_SECONDS:
                        countdown_running = True
                        countdown_remaining = SILENCE_TIMEOUT_SECONDS
                else:
                    countdown_remaining -= check_interval_frames
                    if countdown_remaining <= 0:
                        return None  # full silence timeout, nothing heard

            else:
                chunks.append(frame)
                elapsed = time.time() - recording_start_time

                if speech:
                    silence_start = None
                else:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start > 0.8:
                        return chunks  # trailing silence, utterance done

                if elapsed > MAX_UTTERANCE_SECONDS:
                    return chunks  # hard cap safety


def listen_and_transcribe() -> str | None:
    """
    Records one utterance (or waits through the silence timeout) and
    returns the transcribed text.

    Return values:
      - None  — genuine silence timeout; user never spoke for the full
                4s + 10s window.  Caller should treat as "go to sleep".
      - ""    — VAD triggered but STT rejected the clip (noise / too
                quiet).  Caller should retry listening, NOT sleep.
      - str   — real transcribed speech.
    """
    chunks = _listen_for_turn_or_sleep()
    if chunks is None:
        return None  # genuine silence timeout

    import numpy as np
    audio = np.concatenate(chunks)
    query = transcribe(audio)
    return query.strip()  # "" if noise-rejected, else real text