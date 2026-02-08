from dataclasses import dataclass


@dataclass
class Turn:
    role: str # "user" or "assistant"
    content: str

class ConversationMemory:
    def __init__(self, max_turns: int = 5):
        self.turns: list[Turn] = []
        self.max_turns = max_turns

    def add_user_message(self, message: str):
        self.turns.append(Turn(role="user", content=message))
        self._trim()

    def add_ai_message(self, message: str):
        self.turns.append(Turn(role="assistant", content=message))
        self._trim()

    def _trim(self):
        if len(self.turns) > self.max_turns * 2:
            self.turns = self.turns[-(self.max_turns * 2):]

    def get_history_string(self) -> str:
        return "\n".join([f"{t.role.capitalize()}: {t.content}" for t in self.turns])

    def clear(self):
        self.turns = []
