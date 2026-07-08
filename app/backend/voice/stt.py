import os
import time

import numpy as np
import scipy.io.wavfile
from faster_whisper import WhisperModel

# ---------------------------------------------------------------------------
# Diagnostic controls
# Set DEBUG_AUDIO = True to enable verbose STT diagnostics and WAV saving.
# Flip to False to silence all diagnostic output in production.
# ---------------------------------------------------------------------------
DEBUG_AUDIO = True
DEBUG_WAV_DIR = "voice_debug"

# ---------------------------------------------------------------------------
# Clipping fix
# Normalize audio so peak amplitude never exceeds NORMALIZE_TARGET before
# sending to Whisper. Clipped audio (peak=1.0) distorts phoneme boundaries
# and causes incorrect transcriptions (e.g. "Inventor Gravity" instead of
# "who invented gravity"). This is a post-capture soft-cap; the real fix is
# to lower Windows mic gain, but this prevents Whisper from seeing clipped
# waveforms in the meantime.
# ---------------------------------------------------------------------------
NORMALIZE_TARGET = 0.95

# ---------------------------------------------------------------------------
# Hallucination filter thresholds
# Data across two diagnostic runs:
#
#   Run 1 (pre-normalization, clipped audio):
#     Real speech     no_speech_prob 0.027–0.588  avg_logprob -0.55 to -0.89
#     Hallucinations  no_speech_prob 0.51–0.66    avg_logprob -0.98 to -1.07
#
#   Run 2 (post-normalization — current):
#     Real speech     no_speech_prob 0.003–0.22   avg_logprob -0.57 to -1.07
#     Hallucinations  no_speech_prob 0.31–0.46    avg_logprob -0.52 to -0.66
#
# After normalization fixed the clipping:
#   - no_speech_prob has a CLEAN 0.09 gap (real max 0.22 vs halluc min 0.31)
#   - avg_logprob is NO LONGER a reliable separator: real speech now spans
#     -0.57 to -1.07, fully overlapping both hallucination ranges. Removed.
#
# Primary defence: NO_SPEECH_PROB_THRESHOLD = 0.28 (midpoint of gap).
# Catches both old "Thank you." pattern (0.51–0.66) and new "Bye." (0.31–0.46).
#
# Secondary (pre-Whisper) defence: RMS_SILENCE_THRESHOLD — if the entire
# utterance energy is below this, skip Whisper entirely. More robust than
# relying on Whisper's own scores, which vary with audio content.
# Real speech observed at RMS ~0.10; silence noise expected ~0.001–0.01.
# ---------------------------------------------------------------------------
NO_SPEECH_PROB_THRESHOLD = 0.5
RMS_SILENCE_THRESHOLD = 0.02  # skip Whisper if utterance is likely silence

_model = WhisperModel("small", device="cpu", compute_type="int8")


def _save_debug_wav(audio: np.ndarray) -> str:
    """Save audio to a timestamped WAV file in voice_debug/. Returns the path."""
    os.makedirs(DEBUG_WAV_DIR, exist_ok=True)
    filename = os.path.join(DEBUG_WAV_DIR, f"utterance_{time.strftime('%Y%m%d_%H%M%S')}.wav")
    # scipy expects int16; convert from float32 [-1, 1]
    audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    scipy.io.wavfile.write(filename, 16000, audio_int16)
    return filename


def transcribe(audio: np.ndarray) -> str:
    """
    Takes a 1D float32 numpy array (16kHz, mono) and returns transcribed text.

    Two-layer hallucination defence:
      1. RMS pre-check: if the utterance RMS < RMS_SILENCE_THRESHOLD, return ""
         immediately without calling Whisper. Catches VAD false triggers on
         background noise before any hallucination can occur.
      2. Segment filter: discard any Whisper segment where no_speech_prob >
         NO_SPEECH_PROB_THRESHOLD (0.28). avg_logprob removed — post-
         normalization real speech spans -0.57 to -1.07, making it unreliable.

    Also applies clipping normalization before transcription if peak > 0.95.

    Diagnostic mode (DEBUG_AUDIO=True) logs:
      - Original RMS and peak amplitude (before normalization)
      - Per-segment no_speech_prob, avg_logprob, and keep/discard decision
      - Saves a .wav file (post-normalization) to voice_debug/
    """
    rms = float(np.sqrt(np.mean(audio ** 2)))
    peak = float(np.max(np.abs(audio)))

    if DEBUG_AUDIO:
        print(f"[STT] RMS={rms:.4f}  Peak={peak:.4f}", end="")
        if peak >= 0.99:
            print("  ⚠ CLIPPING — normalizing before transcription (lower Windows mic gain to fix at source)", end="")
        print()

    # --- RMS pre-check: skip Whisper entirely on near-silent audio ---
    # Silero VAD occasionally lets through background noise bursts that
    # would cause Whisper to hallucinate. If the whole utterance is below
    # the silence threshold, there is nothing real to transcribe.
    if rms < RMS_SILENCE_THRESHOLD:
        if DEBUG_AUDIO:
            print(f"[STT] RMS {rms:.4f} below silence threshold {RMS_SILENCE_THRESHOLD} — skipping transcription")
        return ""

    # --- Clipping fix: scale down to NORMALIZE_TARGET if peak exceeds it ---
    if peak > NORMALIZE_TARGET:
        audio = audio * (NORMALIZE_TARGET / peak)
        if DEBUG_AUDIO:
            new_peak = float(np.max(np.abs(audio)))
            print(f"[STT] Normalized: new peak={new_peak:.4f}")

    if DEBUG_AUDIO:
        wav_path = _save_debug_wav(audio)
        print(f"[STT] Saved debug WAV → {wav_path}")

    segments_iter, _info = _model.transcribe(audio, language="en")

    parts = []
    for segment in segments_iter:
        # avg_logprob removed from the filter: post-normalization real speech
        # spans -0.57 to -1.07, making it an unreliable separator. no_speech_prob
        # alone has a clean gap (real max 0.22 vs hallucination min 0.31).
        is_hallucination = segment.no_speech_prob > NO_SPEECH_PROB_THRESHOLD

        if DEBUG_AUDIO:
            verdict = "✗ FILTERED" if is_hallucination else "✓ kept"
            print(
                f"[STT] Segment [{segment.start:.2f}s→{segment.end:.2f}s] "
                f"no_speech_prob={segment.no_speech_prob:.3f}  "
                f"avg_logprob={segment.avg_logprob:.3f}  "
                f"{verdict}  text={segment.text.strip()!r}"
            )

        if not is_hallucination:
            parts.append(segment.text.strip())

    return " ".join(parts).strip()