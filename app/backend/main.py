from app.backend.chat.chain import chat
from app.backend.scheduler.jobs import start_scheduler
from app.backend.memory.sqlite_client import init_db

def is_wake_word(query):
    q = query.lower().strip()
    return any(q.startswith(w) for w in ["hey cyclone", "hy cyclone", "ok cyclone"]) or "cyclone" in q and any(g in q for g in ["hey", "hy", "heyy", "ok"])

def is_sleep_word(query):
    q = query.lower().strip()
    return any(phrase in q for phrase in ["cyclone sleep", "bye cyclone", "see you later", "see u later"])

def main():
    init_db()
    start_scheduler()

    awake = False

    while True:
        query = input("Me: ")
        if query.lower().strip() == "stop": break

        if not awake:
            if is_wake_word(query):
                awake = True
                print("Cyclone: Hey Thunder! I'm here 💙")
            continue

        if is_sleep_word(query):
            awake = False
            print("Cyclone: Going to sleep. Call me when you need me 🌙")
            continue

        response = chat(query)
        print("Cyclone: " + response)

if __name__ == "__main__":
    main()