"""Prints one labelled line per topic and keeps numbers for the final workflow summary."""

STATS = {"emails": 0, "blocked": 0, "pii_hidden": 0, "types": {}, "tool_calls": 0, "rag_searches": 0,
         "approve": 0, "edit": 0, "reject": 0, "replies": 0, "cost": 0.0, "models": set()}
CURRENT = {"path": [], "tools": [], "decisions": []}   # reset for every email


def show(topic: str, message: str):
    print(f"   [{topic}] {message}")


def start_email():
    CURRENT.update(path=["START"], tools=[], decisions=[])
    STATS["emails"] += 1
