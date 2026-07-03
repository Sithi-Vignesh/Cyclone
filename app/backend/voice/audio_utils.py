import sounddevice as sd
import numpy as np

SAMPLE_RATE = 16000  # Whisper expects 16kHz audio


def record_audio(duration_seconds: float) -> np.ndarray:
    """
    Records audio from the default microphone for a fixed duration.
    Returns a 1D numpy array of float32 samples at 16kHz, mono.
    """
    print(f"Recording for {duration_seconds} seconds...")
    audio = sd.rec(
        int(duration_seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
    )
    sd.wait()  # blocks until recording finishes
    print("Recording done.")
    return audio.flatten()