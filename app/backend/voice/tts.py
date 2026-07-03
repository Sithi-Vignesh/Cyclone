from piper import PiperVoice
from piper.config import SynthesisConfig
import numpy as np

_voice = PiperVoice.load("app/backend/voice/models/en_US-libritts-high.onnx")

_syn_config = SynthesisConfig(speaker_id=0)


def synthesize(text: str) -> tuple[np.ndarray, int]:
    """
    Takes text and returns (audio, sample_rate) using the locked speaker (p3922).
    """
    audio_chunks = []
    sample_rate = None

    for chunk in _voice.synthesize(text, syn_config=_syn_config):
        audio_chunks.append(chunk.audio_float_array)
        sample_rate = chunk.sample_rate

    audio = np.concatenate(audio_chunks)
    return audio, sample_rate