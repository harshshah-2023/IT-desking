"""Topic: LLM Gateway (LiteLLM) - Router, fallbacks, caching, routing, cost tracking.

Used to write the final reply email to the customer.
"""
import time
import litellm
from litellm import Router, completion_cost
from litellm.caching import Cache
from app.log import show, STATS

litellm.suppress_debug_info = True
litellm.cache = Cache(type="local")          # same prompt twice -> answered from memory

router = Router(
    model_list=[
        {"model_name": "fast",   "litellm_params": {"model": "gpt-4o-mini"}},
        {"model_name": "smart",  "litellm_params": {"model": "gpt-4o"}},
        {"model_name": "backup", "litellm_params": {"model": "groq/llama-3.3-70b-versatile"}},
    ],
    fallbacks=[{"fast": ["backup"]}, {"smart": ["backup"]}],   # if OpenAI fails, use Groq
)


def draft_reply(ticket: dict, desk_answer: str) -> str:
    """Turn the desk agent's answer into a polite email (routing: access requests -> smart model)."""
    alias = "smart" if ticket["request_type"] == "access_request" else "fast"
    prompt = (
        "Write a short, polite email reply to an employee from the IT Access Desk.\n"
        "Use ONLY the facts in the desk answer. Do not promise anything else. "
        "Start with 'Hi <first name>,' and end with 'Regards,\\nIT Access Desk'.\n\n"
        f"Employee: {ticket['requester']}\nTheir request: {ticket['summary']}\n"
        f"Desk answer: {desk_answer}"
    )

    start = time.time()
    response = router.completion(model=alias, messages=[{"role": "user", "content": prompt}], caching=True)
    seconds = round(time.time() - start, 2)
    try:
        cost = completion_cost(completion_response=response)
    except Exception:
        cost = 0.0
    STATS["cost"] += cost
    STATS["models"].add(response.model)
    show("LLM Gateway", f"route={alias} -> model={response.model} | time={seconds}s | "
                        f"tokens={response.usage.total_tokens} | cost=${cost:.6f}")
    return response.choices[0].message.content
