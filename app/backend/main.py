from app.backend.chat.chain import chat
from app.backend.scheduler.jobs import start_scheduler
from app.backend.memory.sqlite_client import init_db

def main():
    init_db()
    start_scheduler()

    while True:
        query = input("Me: ")
        if query.lower().strip() == "stop" : break
        
        response = chat(query)
        print("Cyclone: " + response)

if __name__ == "__main__":
    main()