import time

import numpy as np
import sounddevice as sd
from openwakeword.model import Model

SAMPLE_RATE = 16000
FRAME_SIZE = 1280  # openWakeWord's expected chunk size (80ms @ 16kHz)
MODEL_NAME = "hey_sie_cloan"

# ---------------------------------------------------------------------------
# Diagnostic controls
# Set DEBUG_WAKE_WORD = True to log raw prediction scores continuously.
# This reveals what confidence levels normal-volume speech actually achieves,
# which is essential before tuning the threshold.
# ---------------------------------------------------------------------------
DEBUG_WAKE_WORD = True
_DEBUG_SCORE_MIN_PRINT = 0.05   # only print scores above this (avoids flooding)
_DEBUG_MAX_REPORT_INTERVAL = 5.0  # log rolling max_score_seen every N seconds

_model = Model(
    wakeword_models=[f"app/backend/voice/models/{MODEL_NAME}.onnx"],
    inference_framework="onnx",
)


def listen_for_wake_word(threshold: float = 0.015) -> None:
    """
    Blocks forever, streaming mic audio in small frames, until the
    wake word is detected. Returns control once detected.

    Threshold set to 0.3 (was 0.5) based on diagnostic data:
    normal speaking volume scores 0.30–0.46; shouting was required to
    cross 0.5. 0.3 catches the low end of normal-volume detections.

    Diagnostic mode (DEBUG_WAKE_WORD=True) logs:
      - Every prediction score above _DEBUG_SCORE_MIN_PRINT
      - A rolling max_score_seen report every _DEBUG_MAX_REPORT_INTERVAL seconds
        so you can see what normal speech achieves vs the current threshold
    """
    last_max_report = time.time()
    max_score_seen = 0.0

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as stream:
        print(f"[WakeWord] Listening... (threshold={threshold})")
        while True:
            frame, _ = stream.read(FRAME_SIZE)
            frame = frame.flatten()
            prediction = _model.predict(frame)
            score = prediction[MODEL_NAME]

            if DEBUG_WAKE_WORD:
                if score > max_score_seen:
                    max_score_seen = score

                if score >= _DEBUG_SCORE_MIN_PRINT:
                    print(f"[WakeWord] score={score:.4f}  (threshold={threshold})")

                now = time.time()
                if now - last_max_report >= _DEBUG_MAX_REPORT_INTERVAL:
                    print(
                        f"[WakeWord] Rolling max score in last {_DEBUG_MAX_REPORT_INTERVAL:.0f}s: "
                        f"{max_score_seen:.4f}  (threshold={threshold})"
                    )
                    max_score_seen = 0.0
                    last_max_report = now

            if score > threshold:
                print(f"[WakeWord] ✓ Wake word detected! score={score:.4f}")
                _model.reset()
                return


if __name__ == "__main__":
    listen_for_wake_word()
    print("Done.")