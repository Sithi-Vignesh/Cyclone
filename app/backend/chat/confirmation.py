import random
import time

_pending = None  # {"action": "shutdown"|"restart", "token": str, "expires": float}
TOKEN_TTL = 60  # seconds

def request_confirmation(action: str) -> str:
    global _pending
    token = str(random.randint(1000, 9999))
    _pending = {"action": action, "token": token, "expires": time.time() + TOKEN_TTL}
    return token

def check_confirmation(action: str, spoken_token: str) -> bool:
    global _pending
    if _pending is None:
        return False
    if _pending["action"] != action:
        return False
    if time.time() > _pending["expires"]:
        _pending = None
        return False
    if spoken_token.strip() != _pending["token"]:
        return False
    _pending = None  # single-use
    return True

def clear_confirmation():
    global _pending
    _pending = None

def get_pending():
    return _pending
