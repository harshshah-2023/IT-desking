"""Topic: LangGraph - the email workflow as a StateGraph.

START -> extract -> desk -> reply -> END
            |                 ^
            +--- blocked -----+
"""
import json
from datetime import datetime
from typing import TypedDict
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END

from app.config import OUTBOX, TICKETS_FILE
from app.guardrails import BLOCKED_MSG
from app.desk import extractor, handle_request
from app.gateway import draft_reply
from app.log import show, STATS


class EmailState(TypedDict, total=False):
    email_id: str
    sender: str
    subject: str
    body: str
    ticket: dict | None
    answer: str
    reply: str


def extract_node(state: EmailState):
    """Guardrails + structured output: read the email into a Ticket."""
    result = extractor.invoke({"messages": [HumanMessage(content=state["body"])]})
    seen_by_model = result["messages"][0].content

    ticket = result.get("structured_response")        # missing if the guardrail blocked it
    if ticket is None:
        STATS["blocked"] += 1
        show("Guardrails", "InjectionFilter BLOCKED this email - the agent never ran")
        return {"ticket": None, "answer": BLOCKED_MSG}

    if seen_by_model != state["body"]:
        STATS["pii_hidden"] += 1
        show("Guardrails", f"PII hidden. Model saw: {seen_by_model[:160]}")
    else:
        show("Guardrails", "no PII or injection found")

    t = ticket.model_dump()
    STATS["types"][t["request_type"]] = STATS["types"].get(t["request_type"], 0) + 1
    show("Structured Output", f"Ticket: {t['requester']} | {t['request_type']} | system={t['system']} | "
                              f"{t['access_level']} | hours={t['duration_hours']} | urgency={t['urgency']}")
    return {"ticket": t}


def route_after_extract(state: EmailState) -> str:
    nxt = "reply" if state["ticket"] is None else "desk"
    show("LangGraph", f"conditional edge after 'extract' -> '{nxt}'")
    return nxt


def desk_node(state: EmailState):
    """Desk agent: tools + policy RAG + human approval."""
    request = f"Ticket: {json.dumps(state['ticket'])}\n\nOriginal email:\n{state['body']}"
    answer = handle_request(request, customer=state["sender"])
    show("Desk Agent", f"final answer: {answer[:200]}")
    return {"answer": answer}


def reply_node(state: EmailState):
    """Write the reply email (via the LLM gateway) to the outbox and log the ticket."""
    if state["ticket"] is None:
        body = ("Hello,\n\nYour message could not be processed because it breaks our IT request rules. "
                "Please send a normal access or support request.\n\nRegards,\nIT Access Desk")
        show("Reply", "fixed 'blocked' reply (no LLM call)")
    else:
        body = draft_reply(state["ticket"], state["answer"])

    reply_file = OUTBOX / f"{state['email_id']}_reply.txt"
    reply_file.write_text(f"To: {state['sender']}\nSubject: Re: {state['subject']}\n\n{body}\n", encoding="utf-8")
    STATS["replies"] += 1

    log = {"email_id": state["email_id"], "from": state["sender"], "time": datetime.now().isoformat(timespec="seconds"),
           "ticket": state["ticket"], "answer": state["answer"]}
    with open(TICKETS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log) + "\n")
    return {"reply": body}


builder = StateGraph(EmailState)
builder.add_node("extract", extract_node)
builder.add_node("desk", desk_node)
builder.add_node("reply", reply_node)
builder.add_edge(START, "extract")
builder.add_conditional_edges("extract", route_after_extract, ["desk", "reply"])
builder.add_edge("desk", "reply")
builder.add_edge("reply", END)
email_graph = builder.compile()
