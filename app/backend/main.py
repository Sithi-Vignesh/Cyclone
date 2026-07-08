import threading

from app.backend.chat.chain import chat
from app.backend.voice.filler import get_filler
from app.backend.scheduler.jobs import start_scheduler
from app.backend.memory.sqlite_client import init_db
from app.backend.core import state
from app.backend.core.error_logger import log_error
from app.backend.voice.voice_loop import (
    wait_for_wake_word,
    listen_and_transcribe,
    speak,
)

ANSWER_TIMEOUT = 30  # not currently enforced here; chat() runs synchronously in both modes


def is_wake_word(query):
    q = query.lower().strip()
    return any(q.startswith(w) for w in ["hey cyclone", "hy cyclone", "ok cyclone"]) or "cyclone" in q and any(g in q for g in ["hey", "hy", "heyy", "ok"])


def is_sleep_word(query):
    q = query.lower().strip()
    return any(phrase in q for phrase in ["cyclone sleep", "bye cyclone", "see you later", "see u later"])


def get_input(mode: str) -> str | None:
    """Gets one turn of user input, either typed or spoken, depending on mode.

    In voice mode, returns None for silence timeout, "" for a noise-rejected
    clip, or the transcribed text.
    """
    if mode == "voice":
        query = listen_and_transcribe()
        if query:
            print(f"Me: {query}")
        return query
    return input("Me: ")


def send_output(mode: str, text: str) -> None:
    """Sends one turn of Cyclone's output, either printed or spoken, depending on mode."""
    print("Cyclone: " + text)
    if mode == "voice":
        speak(text)


def main():
    init_db()
    start_scheduler()

    mode = ""
    while mode not in ("text", "voice"):
        mode = input("Mode? (text/voice): ").strip().lower()

    while True:
        if mode == "voice" and not state.awake:
            # Wake word detection happens via openWakeWord, not typed text —
            # no need to check is_wake_word() against transcribed speech.
            wait_for_wake_word()
            state.awake = True
            send_output(mode, "Hey Thunder! I'm here.")
            continue

        query = get_input(mode)

        if mode == "text" and query.lower().strip() == "stop":
            break

        if query is None:
            # Genuine silence timeout — user never spoke for the full window
            if mode == "voice":
                state.awake = False
                print("Session ended, back to wake word listening.")
            continue

        if query == "":
            # VAD triggered on noise, STT rejected it — just retry listening
            continue

        if not state.awake:
            if is_wake_word(query):
                state.awake = True
                send_output(mode, "Hey Thunder! I'm here 💙")
            continue

        if is_sleep_word(query):
            state.awake = False
            send_output(mode, "Going to sleep. Call me when you need me 🌙")
            continue

        while True:
            # ----------------------------------------------------------------
            # Run chat() in a background thread so the filler can be spoken
            # on the main thread concurrently, masking LLM latency.
            # ----------------------------------------------------------------
            chat_result = {"response": None, "error": None}

            def run_chat():
                try:
                    chat_result["response"] = chat(query)
                except Exception as exc:
                    chat_result["error"] = exc

            chat_thread = threading.Thread(target=run_chat, daemon=True)
            chat_thread.start()

            # Speak filler while chat() works in the background.
            try:
                filler_text = get_filler(query)
                send_output(mode, filler_text)
            except Exception as filler_exc:
                # get_filler() has its own never-raise guarantee, but be safe.
                log_error("main.filler", filler_exc)

            # Block until chat() is done — no-op if it already finished.
            # Filler is always fully played/printed before this returns.
            chat_thread.join()

            # Now inspect the result and mirror the original error handling.
            if chat_result["error"] is None:
                send_output(mode, chat_result["response"])
                break
            elif isinstance(chat_result["error"], ValueError):
                send_output(mode, "Timed out.")
                if mode == "voice":
                    retry_query = listen_and_transcribe()
                else:
                    retry_query = input("Type 'retry' to try again or anything else to skip.\nMe: ")
                if not retry_query or retry_query.lower().strip() not in ("retry", "yes", "yeah", "try again"):
                    break
                # Loop back — next iteration will also use the threaded pattern.
            else:
                log_error("main.chat_loop", chat_result["error"])
                send_output(mode, "Something went wrong on my end — I've logged it. What else can I do for you?")
                break


if __name__ == "__main__":
    main()