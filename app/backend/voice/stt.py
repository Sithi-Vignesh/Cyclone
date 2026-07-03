from faster_whisper import WhisperModel
import numpy as np

_model = WhisperModel("base", device="cpu", compute_type="int8")


def transcribe(audio: np.ndarray) -> str:
    """
    Takes a 1D float32 numpy array (16kHz, mono) and returns transcribed text.
    """
    segments, info = _model.transcribe(audio, language="en")
    text = " ".join(segment.text.strip() for segment in segments)
    return text.strip()