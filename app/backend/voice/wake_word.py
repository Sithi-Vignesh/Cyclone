import sounddevice as sd
import numpy as np
from openwakeword.model import Model

SAMPLE_RATE = 16000
FRAME_SIZE = 1280  # openWakeWord's expected chunk size (80ms @ 16kHz)
MODEL_NAME = "hey_sie_cloan"

_model = Model(
    wakeword_models=[f"app/backend/voice/models/{MODEL_NAME}.onnx"],
    inference_framework="onnx",
)


def listen_for_wake_word(threshold: float = 0.5) -> None:
    """
    Blocks forever, streaming mic audio in small frames, until the
    wake word is detected. Returns control once detected.
    """
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as stream:
        print("Listening for wake word...")
        while True:
            frame, _ = stream.read(FRAME_SIZE)
            frame = frame.flatten()
            prediction = _model.predict(frame)
            if prediction[MODEL_NAME] > threshold:
                print("Wake word detected!")
                _model.reset()
                return
            

if __name__ == "__main__":
    listen_for_wake_word()
    print("Done.")