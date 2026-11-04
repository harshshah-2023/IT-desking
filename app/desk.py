"""Topics: Structured output + Human-in-the-Loop desk agent.

- extractor: turns an email into a clean Ticket (with guardrails).
- desk: the agent that checks the employee, server and policy, and asks a human before granting.
"""
from typing import Literal
from pydantic import BaseModel, Field
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.config import llm
from app.guardrails import GUARDRAILS
from app.tools import check_ad_groups, ping_server_status, grant_system_access
from app.rag import search_policy
from app.log import show, STATS, CURRENT


# ---------------- Structured output ----------------
class Ticket(BaseModel):
    requester: str = Field(description="Full name of the person who wrote the email")
    request_type: Literal["access_request", "it_support", "other"]
    system: str | None = Field(description="System name, e.g. prod-db, aws-prod, vpn, jira")
    access_level: Literal["read", "write", "admin", "none"]
    duration_hours: int | None = Field(description="Requested hours, if given")
    urgency: Literal["low", "medium", "high", "critical"]
    summary: str = Field(description="One-sentence summary of the request")


extractor = create_agent(
    llm,
    tools=[],
    system_prompt="Extract the ticket details from the employee's email.",
    response_format=Ticket,
    middleware=GUARDRAILS,
)


# ---------------- Desk agent with human approval ----------------
desk = create_agent(
    llm,
    tools=[check_ad_groups, ping_server_status, search_policy, grant_system_access],
    system_prompt=(
        "You are the IT Access Desk. You decide access requests yourself; a human manager reviews "
        "every grant automatically when you call grant_system_access.\n"
        "Access requests - follow these steps:\n"
        "1. check_ad_groups: the employee must be active.\n"
        "2. ping_server_status for the system.\n"
        "3. search_policy with a specific question, e.g. 'What is the maximum read access duration for prod-db?'\n"
        "4. If the policy allows the request, CALL grant_system_access (use the employee_id, system, "
        "access_level, hours and the incident ticket as reason). If the requested hours are too long, "
        "call it with the maximum hours the policy allows.\n"
        "5. Refuse only when a policy rule clearly forbids it, and name that rule.\n"
        "Never tell the employee to ask their manager - calling grant_system_access IS the approval step.\n"
        "IT support problems (no access needed): check the server status and give clear next steps.\n"
        "Finish with a short answer for the employee."
    ),
    middleware=[
        *GUARDRAILS,
        HumanInTheLoopMiddleware(interrupt_on={"grant_system_access": True}),
    ],
    checkpointer=MemorySaver(),   # memory per customer (thread_id = their email address)
)


def ask_approver(action: dict) -> dict:
    """Ask the human approver in the terminal."""
    args = action["args"]
    print()
    show("Human-in-the-Loop", "agent PAUSED before grant_system_access - waiting for the approver")
    print("   ==== APPROVAL NEEDED ====")
    print(f"   Grant {args.get('access_level')} on {args.get('system')} to {args.get('employee_id')} "
          f"for {args.get('duration_hours')} hours. Reason: {args.get('reason')}")
    choice = input("   approve / edit / reject: ").strip().lower()
    if choice not in ("edit", "reject"):
        choice = "approve"
    STATS[choice] += 1
    if choice == "edit":
        hours = int(input("   New duration in hours: "))
        CURRENT["decisions"].append(f"edited to {hours}h")
        show("Human-in-the-Loop", f"resumed with EDIT -> {hours} hours")
        return {"type": "edit", "edited_action": {"name": action["name"], "args": {**args, "duration_hours": hours}}}
    if choice == "reject":
        reason = input("   Reason: ")
        CURRENT["decisions"].append(f"rejected ({reason})")
        show("Human-in-the-Loop", f"resumed with REJECT -> {reason}")
        return {"type": "reject", "message": reason}
    CURRENT["decisions"].append("approved")
    show("Human-in-the-Loop", "resumed with APPROVE")
    return {"type": "approve"}


def handle_request(text: str, customer: str) -> str:
    """Run the desk agent; pause for the approver whenever it wants to grant access."""
    config = {"configurable": {"thread_id": customer}}
    before = len(desk.get_state(config).values.get("messages", []))
    show("Memory", f"thread_id={customer} | messages remembered from earlier emails: {before}")
    show("LangGraph agent", "ReAct loop started: model -> tools -> model ... (create_agent)")
    result = desk.invoke({"messages": [HumanMessage(content=text)]}, config)
    while "__interrupt__" in result:
        actions = result["__interrupt__"][0].value["action_requests"]
        decisions = [ask_approver(a) for a in actions]
        result = desk.invoke(Command(resume={"decisions": decisions}), config)
    return result["messages"][-1].content
