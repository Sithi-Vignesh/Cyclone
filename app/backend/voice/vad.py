import torch
import numpy as np

# Loaded once at import time, same reasoning as stt.py's model loading.
_model, _utils = torch.hub.load(
    repo_or_dir="snakers4/silero-vad",
    model="silero_vad",
    force_reload=False,
)

SAMPLE_RATE = 16000
CHUNK_SIZE = 512  # samples per chunk, required by Silero VAD at 16kHz


def reset_vad() -> None:
    """Reset Silero VAD internal state (call after TTS to prevent carryover)."""
    _model.reset_states()


def is_speech(audio_chunk: np.ndarray, threshold: float = 0.5) -> bool:
    """
    Takes a single chunk of float32 audio (length == CHUNK_SIZE) and
    returns True if Silero VAD thinks it contains speech.
    """
    tensor_chunk = torch.from_numpy(audio_chunk)
    speech_prob = _model(tensor_chunk, SAMPLE_RATE).item()
    return speech_prob >= threshold