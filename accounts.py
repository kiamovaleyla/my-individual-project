import csv
import hashlib
import secrets

from models import HashTable

ACCOUNTS_FILE = "accounts.csv"

# токен -> имя пользователя
SESSIONS = HashTable()


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def load_users():
    users = HashTable()
    with open(ACCOUNTS_FILE, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            users.put(row["username"], row["password_hash"])
    return users


def check_credentials(username, password):
    users = load_users()
    if users.contains(username):
        if users.get(username) == hash_password(password):
            return True
    return False


def create_session(username):
    token = secrets.token_hex(16)
    SESSIONS.put(token, username)
    return token


def get_current_user(request):
    token = request.cookies.get("session_id")
    return SESSIONS.get(token)


def delete_session(request):
    token = request.cookies.get("session_id")
    SESSIONS.remove(token)