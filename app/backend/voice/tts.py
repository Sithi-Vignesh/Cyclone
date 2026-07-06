from piper import PiperVoice
from piper.config import SynthesisConfig
import numpy as np

_voice = PiperVoice.load("app/backend/voice/models/en_US-libritts-high.onnx")

_syn_config = SynthesisConfig(speaker_id=0)


def _crossfade(a: np.ndarray, b: np.ndarray, overlap_samples: int) -> np.ndarray:
    """
    Blends the tail of `a` into the head of `b` over `overlap_samples` using a
    linear crossfade, then returns the full concatenated result.

    Layout of the returned array:
      [ a's non-overlapping body | blended overlap | b's non-overlapping tail ]
    """
    # Guard: if either chunk is shorter than the overlap window, skip blending.
    overlap = min(overlap_samples, len(a), len(b))

    a_body = a[:-overlap] if overlap else a
    a_tail = a[-overlap:] if overlap else np.array([], dtype=a.dtype)

    b_head = b[:overlap] if overlap else np.array([], dtype=b.dtype)
    b_tail = b[overlap:] if overlap else b

    if overlap:
        fade_out = np.linspace(1.0, 0.0, overlap, dtype=np.float32)
        fade_in  = np.linspace(0.0, 1.0, overlap, dtype=np.float32)
        blended  = a_tail * fade_out + b_head * fade_in
        return np.concatenate([a_body, blended, b_tail])
    else:
        return np.concatenate([a, b])


def _crossfade_split(
    a: np.ndarray, b: np.ndarray, overlap_samples: int
) -> tuple[np.ndarray, np.ndarray]:
    """
    Streaming variant of _crossfade: same linear fade math, but instead of
    returning one concatenated array it returns a 2-tuple:

      (finished_piece, new_held_chunk)

    ``finished_piece``  — the non-overlapping body of `a`; safe to yield/play
                          immediately because it will never be modified again.
    ``new_held_chunk``  — the blended overlap region concatenated with the
                          non-overlapping tail of `b`; held back so it can be
                          crossfaded with the *next* incoming chunk.

    Concatenating finished_piece + new_held_chunk is identical to what
    _crossfade(a, b, overlap_samples) would have returned.
    """
    overlap = min(overlap_samples, len(a), len(b))

    a_body = a[:-overlap] if overlap else a
    a_tail = a[-overlap:] if overlap else np.array([], dtype=a.dtype)

    b_head = b[:overlap] if overlap else np.array([], dtype=b.dtype)
    b_tail = b[overlap:] if overlap else b

    if overlap:
        fade_out = np.linspace(1.0, 0.0, overlap, dtype=np.float32)
        fade_in  = np.linspace(0.0, 1.0, overlap, dtype=np.float32)
        blended  = a_tail * fade_out + b_head * fade_in
        # finished_piece: everything in `a` before the overlap zone.
        finished_piece = np.ascontiguousarray(a_body)
        # new_held_chunk: blended seam + remainder of `b` not yet crossfaded.
        new_held_chunk = np.ascontiguousarray(np.concatenate([blended, b_tail]))
    else:
        # No blending possible; yield all of `a`, hold all of `b`.
        finished_piece = np.ascontiguousarray(a)
        new_held_chunk = np.ascontiguousarray(b)

    return finished_piece, new_held_chunk


def synthesize(text: str):
    """
    Generator that yields (audio_piece, sample_rate) tuples incrementally,
    using 1-chunk-lookahead crossfading so playback can start after only
    ~2 chunks are ready instead of waiting for the entire text to be synthesized.

    Chunk boundaries are smoothed with the same 20 ms linear crossfade used
    previously. The final piece has 150 ms of trailing silence appended so
    playback doesn't clip the last phoneme.

    Yields nothing if the underlying synthesizer produces no chunks (empty
    text or silence-only input).
    """
    held_chunk: np.ndarray | None = None
    sample_rate: int | None = None

    for chunk in _voice.synthesize(text, syn_config=_syn_config):
        sample_rate = chunk.sample_rate
        chunk_audio = np.ascontiguousarray(chunk.audio_float_array)

        if held_chunk is None:
            # First chunk: buffer it; we need the next chunk to crossfade.
            held_chunk = chunk_audio
            continue

        # We have a lookahead chunk: split the crossfade so we can yield
        # the finished (non-overlapping) head of held_chunk right now.
        overlap_samples = int(0.02 * sample_rate)  # 20 ms
        finished_piece, held_chunk = _crossfade_split(
            held_chunk, chunk_audio, overlap_samples
        )

        if len(finished_piece) > 0:
            yield finished_piece, sample_rate

    # After the loop: flush whatever is still held, with trailing silence.
    if held_chunk is not None and sample_rate is not None:
        silence = np.zeros(int(0.15 * sample_rate), dtype=np.float32)
        final_piece = np.ascontiguousarray(np.concatenate([held_chunk, silence]))
        yield final_piece, sample_rate