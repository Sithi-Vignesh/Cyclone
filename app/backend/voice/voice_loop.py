import queue
import threading
import time

import numpy as np
import sounddevice as sd

from app.backend.voice.wake_word import listen_for_wake_word as _listen_for_wake_word
from app.backend.voice.vad import is_speech, reset_vad, CHUNK_SIZE, SAMPLE_RATE
from app.backend.voice.stt import transcribe
from app.backend.voice.tts import synthesize

# Sentinel object placed on the audio queue by the producer thread to signal
# that synthesis is complete and no more audio pieces will be enqueued.
_SENTINEL = object()

POST_TTS_COOLDOWN_SECONDS = 0.3  # let mic AGC settle after TTS playback

SILENCE_TIMEOUT_SECONDS = 6
RESUME_TIMER_AFTER_PAUSE_SECONDS = 4
MAX_UTTERANCE_SECONDS = 15  # safety cap on a single recording, prevents runaway listening


# Fixed callback block size (frames per callback invocation).
# At 22 050 Hz this is ~46 ms — large enough to give PortAudio a stable
# budget without accumulating perceptible latency.
_BLOCKSIZE = 2048


def speak(text: str) -> None:
    """Synthesize and stream-play text via a producer/consumer queue.

    Architecture
    ------------
    Producer thread  — iterates synthesize(text), puts (piece, sample_rate)
                       tuples onto audio_queue, then puts _SENTINEL.
    Callback thread  — called by PortAudio every _BLOCKSIZE frames; drains
                       _pending first, then pulls from audio_queue, outputs
                       silence on underrun (no blocking), raises CallbackStop
                       when _SENTINEL has been received and _pending is empty.
    Main thread      — blocks on done_event.wait() until the callback signals
                       completion, then runs the post-TTS cooldown.

    This decouples synthesis latency from PortAudio's fixed-size block
    schedule, eliminating both the crackle (irregular write sizes) and the
    dead-air gaps (slow inter-sentence chunk production).
    """
    audio_queue: queue.Queue = queue.Queue()
    done_event = threading.Event()

    # ------------------------------------------------------------------ #
    # Producer: run synthesize() in a background thread so PortAudio's    #
    # callback thread is never stalled waiting for Piper to finish a chunk #
    # ------------------------------------------------------------------ #
    def _producer() -> None:
        try:
            for piece, sr in synthesize(text):
                audio_queue.put((piece, sr))
        finally:
            audio_queue.put(_SENTINEL)

    producer_thread = threading.Thread(target=_producer, daemon=True)

    # Block until the FIRST item is available so we know sample_rate before
    # constructing the stream.  The producer thread handles the rest.
    producer_thread.start()
    first_item = audio_queue.get()  # blocks until producer emits something

    if first_item is _SENTINEL:
        # synthesize() yielded nothing (empty text) — skip playback entirely.
        time.sleep(POST_TTS_COOLDOWN_SECONDS)
        reset_vad()
        return

    first_piece, sample_rate = first_item

    # ------------------------------------------------------------------ #
    # _pending: leftover audio not yet consumed by the callback.           #
    # Shape is always (N, 1) — matches outdata's expected layout.          #
    # Only touched inside the callback; the producer only touches the queue #
    # ------------------------------------------------------------------ #
    _pending: list[np.ndarray] = [first_piece.reshape(-1, 1)]
    _sentinel_received: list[bool] = [False]  # mutable flag visible to callback

    # ------------------------------------------------------------------ #
    # Callback: called by PortAudio's internal thread every _BLOCKSIZE     #
    # frames.  Must never block.                                           #
    # ------------------------------------------------------------------ #
    def _callback(
        outdata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        needed = frames  # samples still to fill in this callback
        write_pos = 0    # cursor into outdata

        while needed > 0:
            # --- drain _pending first -----------------------------------
            if _pending:
                chunk = _pending[0]
                if len(chunk) <= needed:
                    # Consume whole chunk
                    outdata[write_pos : write_pos + len(chunk)] = chunk
                    write_pos += len(chunk)
                    needed -= len(chunk)
                    _pending.pop(0)
                else:
                    # Consume partial chunk, leave remainder
                    outdata[write_pos : write_pos + needed] = chunk[:needed]
                    _pending[0] = chunk[needed:]
                    needed = 0
                continue

            # --- _pending is empty: try the queue (non-blocking) --------
            if _sentinel_received[0]:
                # No more audio coming and nothing left to play.
                outdata[write_pos:] = 0  # fill remainder with silence
                done_event.set()
                raise sd.CallbackStop

            try:
                item = audio_queue.get_nowait()
            except queue.Empty:
                # Queue temporarily empty (producer still working):
                # output silence for the missing samples to avoid underrun
                # distortion; a brief clean gap is far less jarring.
                outdata[write_pos:] = 0
                return

            if item is _SENTINEL:
                _sentinel_received[0] = True
                # Loop back: will hit the sentinel branch above on next iter
                continue

            piece, _ = item
            _pending.append(piece.reshape(-1, 1))

        # outdata fully filled
        if needed == 0 and write_pos == frames:
            pass  # normal exit

    # ------------------------------------------------------------------ #
    # Open callback-based stream and wait for completion                   #
    # ------------------------------------------------------------------ #
    with sd.OutputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        blocksize=_BLOCKSIZE,
        callback=_callback,
    ):
        done_event.wait()  # blocks until callback raises CallbackStop

    producer_thread.join()  # ensure producer has fully exited
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

    audio = np.concatenate(chunks)
    query = transcribe(audio)
    return query.strip()  # "" if noise-rejected, else real text