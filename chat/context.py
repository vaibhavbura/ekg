from typing import List, Dict

class ChatContext:
    def __init__(self):
        self.history: List[Dict] = []

    def add_user_message(self, content: str):
        self.history.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str):
        self.history.append({"role": "assistant", "content": content})

    def get_messages(self) -> List[Dict]:
        return self.history
