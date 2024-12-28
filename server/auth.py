import json
from pathlib import Path

class UserAuth:
    def __init__(self):
        self.users_file = Path("users.json")
        self.users = self._load_users()
        
    def _load_users(self):
        if not self.users_file.exists():
            default_users = {
                "admin": {
                    "password": "admin123",
                    "permissions": ["read", "write", "delete"]
                },
                "anonymous": {
                    "password": "",
                    "permissions": ["read"]
                }
            }
            self.users_file.write_text(json.dumps(default_users, indent=2))
            return default_users
        return json.loads(self.users_file.read_text())
        
    def authenticate_user(self, username, password):
        if username not in self.users:
            return False
        if username == "anonymous":
            return True
        return self.users[username]["password"] == password

    def get_user_permissions(self, username):
        return self.users.get(username, {}).get("permissions", [])

auth = UserAuth()
authenticate_user = auth.authenticate_user
get_user_permissions = auth.get_user_permissions 