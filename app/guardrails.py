"""Topic: Guardrails - built-in PIIMiddleware + a custom AgentMiddleware."""
from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config, PIIMiddleware
from langgraph.runtime import Runtime

BLOCKED_MSG = "Blocked: prompt injection detected."
BANNED_PHRASES = ["ignore previous instructions", "ignore all rules", "system prompt", "drop database"]


class InjectionFilter(AgentMiddleware):
    """Stops the agent before it runs if the message tries to override its rules."""

    @hook_config(can_jump_to=["end"])
    def before_agent(self, state: AgentState, runtime: Runtime):
        text = str(state["messages"][-1].content).lower()
        if any(phrase in text for phrase in BANNED_PHRASES):
            return {"messages": [{"role": "assistant", "content": BLOCKED_MSG}], "jump_to": "end"}
        return None


GUARDRAILS = [
    InjectionFilter(),
    PIIMiddleware("email", strategy="redact", apply_to_input=True),        # -> [REDACTED_EMAIL]
    PIIMiddleware("credit_card", strategy="mask", apply_to_input=True),    # -> **** **** **** 1111
    PIIMiddleware("phone", detector=r"(?:\+\d{1,3}[ -]?)?\b\d{5}[ -]?\d{5}\b",
                  strategy="redact", apply_to_input=True),                 # -> [REDACTED_PHONE]
]
