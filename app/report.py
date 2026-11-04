"""Topic: Deep Agents - end-of-day compliance report with a sub-agent and files."""
import json
from datetime import date
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from app.config import llm, OUTPUT, TICKETS_FILE
from app.tools import EMPLOYEES, load_grants


@tool
def get_employee_records() -> str:
    """All employees with status, type, MFA enrollment and AD groups."""
    return json.dumps(list(EMPLOYEES.values()))


@tool
def get_todays_grants() -> str:
    """All access grants approved today."""
    return json.dumps([g for g in load_grants() if g["date"] == str(date.today())])


@tool
def get_todays_tickets() -> str:
    """All emails processed today with their ticket and the desk's answer."""
    if not TICKETS_FILE.exists():
        return "[]"
    lines = TICKETS_FILE.read_text(encoding="utf-8").splitlines()
    return json.dumps([json.loads(l) for l in lines if json.loads(l)["time"].startswith(str(date.today()))])


auditor = {
    "name": "auditor",
    "description": "Checks employees, today's grants and today's tickets for compliance problems.",
    "system_prompt": ("Use your tools. Report: leavers or contractors who still have access, today's grants, "
                      "anyone without MFA, and a count of today's tickets by type. "
                      "Use only names and IDs from the tool output."),
    "tools": [get_employee_records, get_todays_grants, get_todays_tickets],
}

deep_agent = create_deep_agent(
    model=llm,
    system_prompt=("You are the compliance lead. Ask the auditor sub-agent for its findings, "
                   "then write an End-of-Day Compliance Report in Markdown to /eod_compliance_report.md."),
    subagents=[auditor],
    backend=FilesystemBackend(root_dir=OUTPUT, virtual_mode=True),
)


def make_report():
    print("   [Deep Agents] lead agent started (sub-agent: auditor, files saved to output/)")
    result = deep_agent.invoke({"messages": [HumanMessage(content="Create today's compliance report.")]})
    for msg in result["messages"]:
        for call in getattr(msg, "tool_calls", None) or []:
            if call["name"] == "task":
                print(f"   [Deep Agents] delegated to sub-agent '{call['args'].get('subagent_type')}'")
            else:
                print(f"   [Deep Agents] used tool {call['name']}({str(call['args'])[:80]})")
    report = OUTPUT / "eod_compliance_report.md"
    print(report.read_text(encoding="utf-8"))
    print(f"\n   [Deep Agents] report saved to {report}")
