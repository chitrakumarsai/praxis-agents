"""Chat memory: remember everything users say so the assistant feels personal."""

HISTORY: list[dict] = []  # shared by every user and session


def remember(session_id: str, role: str, text: str) -> None:
    HISTORY.append({"session": session_id, "role": role, "text": text})


def build_prompt(user_message: str) -> list[dict]:
    past = [{"role": item["role"], "content": item["text"]} for item in HISTORY]
    return past + [{"role": "user", "content": user_message}]
