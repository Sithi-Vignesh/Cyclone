from app.backend.chat.chain import chat
from app.backend.scheduler.jobs import start_scheduler
from app.backend.memory.sqlite_client import init_db
from app.backend.core import state

def is_wake_word(query):
    q = query.lower().strip()
    return any(q.startswith(w) for w in ["hey cyclone", "hy cyclone", "ok cyclone"]) or "cyclone" in q and any(g in q for g in ["hey", "hy", "heyy", "ok"])

def is_sleep_word(query):
    q = query.lower().strip()
    return any(phrase in q for phrase in ["cyclone sleep", "bye cyclone", "see you later", "see u later"])

def main():
    init_db()
    start_scheduler()

    while True:
        query = input("Me: ")
        if query.lower().strip() == "stop": break

        if not state.awake:
            if is_wake_word(query):
                state.awake = True
                print("Cyclone: Hey Thunder! I'm here 💙")
            continue

        if is_sleep_word(query):
            state.awake = False
            print("Cyclone: Going to sleep. Call me when you need me 🌙")
            continue

        while True:
            try:
                response = chat(query)
                print("Cyclone: " + response)
                break
            except ValueError:
                print("Cyclone: Timed out. Type 'retry' to try again or anything else to skip.")
                user_input = input("Me: ").lower().strip()
                if user_input != "retry":
                    break

if __name__ == "__main__":
    main()