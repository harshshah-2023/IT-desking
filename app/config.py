"""Shared settings: API keys, the LangChain model, and folder paths."""
from pathlib import Path
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv(override=True)   # .env values win over old Windows environment variables

ROOT = Path(__file__).resolve().parent.parent
OUTBOX = ROOT / "outbox"          # replies are written here
OUTPUT = ROOT / "output"          # logs and reports

for folder in (OUTBOX, OUTPUT):
    folder.mkdir(exist_ok=True)

EMPLOYEES_FILE = ROOT / "employees.json"
POLICY_FILE = ROOT / "it_security_policy.md"
GRANTS_FILE = OUTPUT / "grants_audit_log.json"
TICKETS_FILE = OUTPUT / "tickets.jsonl"
DONE_FILE = OUTPUT / "processed_emails.txt"   # emails already answered

llm = init_chat_model("openai:gpt-4o-mini")   # one LangChain model for every agent
