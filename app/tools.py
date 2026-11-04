"""Topic: Tools - read-only lookups and one high-risk action."""
import json
from datetime import date
from langchain_core.tools import tool
from app.config import EMPLOYEES_FILE, GRANTS_FILE
from app.log import show, STATS, CURRENT

EMPLOYEES = {e["employee_id"]: e for e in json.loads(EMPLOYEES_FILE.read_text(encoding="utf-8"))}
SERVERS = {"prod-db": "Healthy", "aws-prod": "Healthy",
           "vpn": "Degraded (Mumbai gateway overloaded, Pune gateway healthy)", "jira": "Healthy"}


def log_tool(name: str, args: str, result) -> None:
    STATS["tool_calls"] += 1
    CURRENT["tools"].append(name)
    show("Tools", f"{name}({args}) -> {str(result)[:120]}")


def load_grants() -> list:
    return json.loads(GRANTS_FILE.read_text(encoding="utf-8")) if GRANTS_FILE.exists() else []


@tool
def check_ad_groups(employee_name_or_id: str) -> dict:
    """Look up an employee's status, type, MFA enrollment, AD groups and manager."""
    for emp in EMPLOYEES.values():
        if employee_name_or_id.lower() in (emp["name"].lower(), emp["employee_id"].lower()):
            log_tool("check_ad_groups", employee_name_or_id,
                     f"{emp['name']}, {emp['status']}, {emp['type']}, MFA={emp['mfa_enrolled']}")
            return emp
    log_tool("check_ad_groups", employee_name_or_id, "not found")
    return {"error": "Employee not found"}


@tool
def ping_server_status(server_name: str) -> str:
    """Check the health of a server: prod-db, aws-prod, vpn or jira."""
    status = SERVERS.get(server_name.lower(), "Unknown server")
    log_tool("ping_server_status", server_name, status)
    return status


@tool
def grant_system_access(employee_id: str, system: str, access_level: str, duration_hours: int, reason: str) -> str:
    """HIGH RISK: give an employee temporary access to a system. Needs human approval."""
    emp = EMPLOYEES[employee_id]
    emp["current_ad_groups"].append(f"{system}-{access_level}")
    grants = load_grants()
    grants.append({"date": str(date.today()), "employee_id": employee_id, "name": emp["name"],
                   "system": system, "level": access_level, "hours": duration_hours, "reason": reason})
    GRANTS_FILE.write_text(json.dumps(grants, indent=2), encoding="utf-8")   
    result = f"Granted {access_level} on {system} to {emp['name']} for {duration_hours} hours."
    log_tool("grant_system_access", f"{employee_id}, {system}, {access_level}, {duration_hours}h", result)
    return result
