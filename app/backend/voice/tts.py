import re

import numpy as np
from num2words import num2words
from piper import PiperVoice
from piper.config import SynthesisConfig

_voice = PiperVoice.load("app/backend/voice/models/en_US-libritts-high.onnx")

_syn_config = SynthesisConfig(speaker_id=0)


# ---------------------------------------------------------------------------
# Text normalisation helpers
# ---------------------------------------------------------------------------

# Regex: full URLs (http/https/ftp/www variants)
_URL_RE = re.compile(
    r"https?://\S+|ftp://\S+|www\.\S+",
    re.IGNORECASE,
)

# Regex: emoji Unicode blocks — strip before any TTS processing.
# Covers emoticons, pictographs, transport, flags, dingbats, supplemental
# symbols, misc symbols, and variation selectors (which modify emoji appearance).
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # symbols & pictographs, extended pictographs
    "\U0001F1E0-\U0001F1FF"  # regional indicator letters (flags)
    "\U00002700-\U000027BF"  # dingbats
    "\U0001F900-\U0001F9FF"  # supplemental symbols & pictographs
    "\U00002600-\U000026FF"  # miscellaneous symbols
    "\U0000FE00-\U0000FE0F"  # variation selectors (emoji presentation modifiers)
    "]+",
    flags=re.UNICODE,
)

# Regex: math operators between two digit characters.
# Must run BEFORE the markdown-strip step so that "15 * 2" is spoken as
# "fifteen times two" rather than having the "*" silently removed.
# The [^\w\n]{0,3} gap allows up to 3 non-word chars (spaces, %, etc.)
# between the digit and the operator, catching cases like "15% * 2".
_MATH_MUL_RE = re.compile(r"(\d)[^\w\n]{0,3}\*[^\w\n]{0,3}(\d)")
_MATH_DIV_RE = re.compile(r"(\d)[^\w\n]{0,3}/[^\w\n]{0,3}(\d)")

# Regex: markdown structural characters
#   • Leading list markers at line start: "- " or "* "
#   • Inline bold/italic/code markers: **, *, __, _, `, #
_MD_LIST_RE = re.compile(r"^[\-\*]\s+", re.MULTILINE)
_MD_INLINE_RE = re.compile(r"[*_`#]+")

# Regex: HH:MM time patterns (24-hour, optional leading zero on single-digit hours)
#   Matches: "6:00", "06:00", "18:30", "00:00", "9:05"
#   Negative look-ahead/look-behind prevents matching e.g. version strings like "1.2:3"
_TIME_RE = re.compile(
    r"(?<!\d)"           # not preceded by a digit
    r"([01]?\d|2[0-3])"  # hours: 0-23, with optional leading zero
    r":"
    r"([0-5]\d)"         # minutes: 00-59
    r"(?!\d)",           # not followed by a digit
)

# Regex: standalone numbers (integers with optional comma-thousands, or decimals).
# Runs AFTER the time step so "18" in "18:00" is already consumed.
_NUMBER_RE = re.compile(
    r"(?<!\d)"                    # not preceded by digit (avoids mid-word matches)
    r"(\d{1,3}(?:,\d{3})*"       # integer, optionally with comma-thousands
    r"(?:\.\d+)?)"                # optional decimal part
    r"(?!\d)",                    # not followed by digit
)


def _time_to_speech(match: re.Match) -> str:
    """Convert a HH:MM regex match to a natural spoken-English string."""
    hour = int(match.group(1))
    minute = int(match.group(2))

    # Special cases first
    if hour == 0 and minute == 0:
        return "midnight"
    if hour == 12 and minute == 0:
        return "noon"

    # Determine AM / PM and convert to 12-hour
    period = "AM" if hour < 12 else "PM"
    hour_12 = hour % 12
    if hour_12 == 0:
        hour_12 = 12  # 00:xx -> 12:xx AM, 12:xx already handled above

    hour_word = num2words(hour_12)  # e.g. "six", "nine"

    if minute == 0:
        return f"{hour_word} {period}"

    # Minutes: treat single-digit minutes as "oh N" (e.g. "oh five")
    if minute < 10:
        minute_word = f"oh {num2words(minute)}"
    else:
        minute_word = num2words(minute)  # e.g. "thirty", "forty-five"

    return f"{hour_word} {minute_word} {period}"


def _number_to_speech(match: re.Match) -> str:
    """Convert a number regex match to spoken English via num2words."""
    raw = match.group(1).replace(",", "")  # strip thousand-separators

    if "." in raw:
        # Split on decimal point and speak each part separately
        int_part, dec_part = raw.split(".", 1)
        int_words = num2words(int(int_part)) if int_part else "zero"
        # Speak decimal digits individually: "3.14" -> "three point one four"
        dec_words = " ".join(num2words(int(d)) for d in dec_part)
        return f"{int_words} point {dec_words}"
    else:
        return num2words(int(raw))


def normalize_for_speech(text: str) -> str:
    """
    Pre-process LLM-generated text before sending it to Piper TTS so that
    numbers, times, symbols, and links are rendered as natural spoken English.

    Transformations are applied in this order (order matters):
      a0. Convert math operators between digits to spoken words
      a. Strip URLs, emojis, and markdown formatting characters
      b. Convert HH:MM time patterns to spoken form
      c. Convert remaining standalone numbers to words via num2words
      d. Replace stray symbols (%, &, /) with spoken equivalents
    """
    # ------------------------------------------------------------------
    # (a0) Speak math operators BEFORE markdown stripping removes them.
    #      Only matches when the operator sits between two digit chars,
    #      so bare markdown "*bold*" is unaffected and still stripped below.
    # ------------------------------------------------------------------
    text = _MATH_MUL_RE.sub(r"\1 times \2", text)
    text = _MATH_DIV_RE.sub(r"\1 divided by \2", text)

    # ------------------------------------------------------------------
    # (a) Strip URLs, emojis, and markdown formatting characters.
    #     Emojis are treated as pure visual noise — remove before any
    #     number/time conversion so they can't interfere with patterns.
    #     The final whitespace-collapse pass at the end of this function
    #     cleans up any spaces left behind (e.g. trailing emoji on a line).
    # ------------------------------------------------------------------
    text = _URL_RE.sub("", text)          # remove URLs entirely
    text = _EMOJI_RE.sub("", text)        # remove all emoji codepoints
    text = _MD_LIST_RE.sub("", text)      # remove leading list markers
    text = _MD_INLINE_RE.sub("", text)    # remove *, _, `, # inline

    # ------------------------------------------------------------------
    # (b) Convert time patterns (HH:MM) BEFORE general number conversion
    #     so that "18:00" is consumed here and the "18" / "00" are never
    #     seen by the number regex.
    # ------------------------------------------------------------------
    text = _TIME_RE.sub(_time_to_speech, text)

    # ------------------------------------------------------------------
    # (c) Convert remaining standalone numbers to words
    # ------------------------------------------------------------------
    text = _NUMBER_RE.sub(_number_to_speech, text)

    # ------------------------------------------------------------------
    # (d) Replace remaining stray symbols
    # ------------------------------------------------------------------
    text = text.replace("%", " percent")
    text = text.replace("&", " and ")
    text = text.replace("/", " or ")

    # Tidy up runs of whitespace that may have been introduced
    text = re.sub(r" {2,}", " ", text).strip()

    return text


# ---------------------------------------------------------------------------
# TTS synthesis
# ---------------------------------------------------------------------------

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
    text = normalize_for_speech(text)

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


# ---------------------------------------------------------------------------
# Quick smoke-test (matches the project pattern in wake_word.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_cases = [
        "The meeting is at 18:00",
        "I have 123 apples",
        "Revenue grew by 15% * 2",
        "Check http://example.com/page for details",
        "The temperature is 3.14 degrees",
    ]
    for tc in test_cases:
        print(f"IN : {tc!r}")
        print(f"OUT: {normalize_for_speech(tc)!r}")
        print()