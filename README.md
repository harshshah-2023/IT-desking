# IT Access & Compliance Triage Desk

An employee sends an email. The AI agent reads it, checks the employee, the server and the
company policy, asks a manager to approve if access is needed, and sends a reply email.

Built only with the topics from Krish Naik's
"Complete Agentic AI Course In 10 Hours".

## The full flow

```
 Employee                     AI Triage Desk (main.py)                          Manager
 --------                     ------------------------                          -------
 mail folder    ────────────► 1. extract  (Guardrails + Structured output)
                                    │  blocked? ──────────────────────┐
                                    ▼                                 │
                               2. desk agent (Tools + Vectorless RAG) │
                                    │  wants to grant access?         │
                                    ├────── approve / edit / reject ◄─┼──── types in terminal
                                    ▼                                 │
                               3. reply (LLM Gateway writes email) ◄──┘
 outbox/  ◄─────────────────────────┘
                               (whole flow = LangGraph StateGraph)

 End of day:  uv run main.py report  ──► Deep Agent ──► output/eod_compliance_report.md
 Quality:     uv run main.py eval    ──► LangSmith evaluates Vector RAG vs Vectorless RAG
```

## Where each video topic is used

| Video topic | File | What it does in the flow |
|-------------|------|--------------------------|
| LangChain (structured output) | `app/desk.py` | Turns the email into a `Ticket` |
| Guardrails (PII + custom middleware) | `app/guardrails.py` | Hides email/phone/card, blocks prompt injection |
| Tools | `app/tools.py` | Look up employee, check server, grant access |
| Vectorless RAG | `app/rag.py` | `search_policy` tool used by the desk agent |
| Vector RAG (FAISS) | `app/rag.py` | Compared with vectorless RAG in the evaluation |
| Human-in-the-Loop | `app/desk.py` | Pauses before every grant for manager approval |
| LangGraph | `app/pipeline.py` | The email workflow: extract → desk → reply |
| LLM Gateway (LiteLLM) | `app/gateway.py` | Writes the reply email: routing, fallback, cache, cost |
| Deep Agents | `app/report.py` | End-of-day compliance report with a sub-agent |
| LLM Evaluation (LangSmith) | `app/evals.py` | Scores both RAG systems on a golden dataset |

The notebook `access_triage_desk_simple.ipynb` explains every topic step by step.

## Setup (uv, same steps as the video)

```powershell
uv init
uv venv
.venv\Scripts\activate
uv add -r requirements.txt
copy .env.example .env
```

Open `.env` and add your keys (`OPENAI_API_KEY` is required; `GROQ_API_KEY` is the backup model;
`LANGSMITH_API_KEY` is needed for `eval`). `uv init` keeps the existing `main.py`.

## Run the full flow

Give the folder that contains the emails:
```powershell
uv run main.py sample_emails
```
Or just run `uv run main.py` and type the folder name when it asks.

### What you will see
1. **The LangGraph graph** of the email workflow (drawn in the terminal), and
   `output/langgraph_graphs.html` with both graphs as pictures (open it in your browser).
2. **For every email, one labelled line per topic**, for example:
```
   [Guardrails] PII hidden. Model saw: ... You can reach me on [REDACTED_PHONE]. Thanks!
   [Structured Output] Ticket: Divya Pillai | access_request | system=prod-db | read | hours=48 | urgency=high
   [LangGraph] conditional edge after 'extract' -> 'desk'
   [Memory] thread_id=divya.pillai@acme.com | messages remembered from earlier emails: 0
   [LangGraph agent] ReAct loop started: model -> tools -> model ... (create_agent)
   [Tools] check_ad_groups(EMP-2002) -> Divya Pillai, active, employee, MFA=True
   [Tools] search_policy(max read access hours on prod-db)
   [Vectorless RAG] LLM picked sections: ['1.3 Read Access']
   [Human-in-the-Loop] agent PAUSED before grant_system_access - waiting for the approver
   approve / edit / reject: approve
   [Tools] grant_system_access(EMP-2002, prod-db, read, 48h) -> Granted ...
   [LLM Gateway] route=smart -> model=gpt-4o | time=1.2s | tokens=310 | cost=$0.001200
```
3. **A summary for each email**: graph path, ticket, tools used, approval, and the reply email.
4. **"HOW YOUR WORKFLOW WORKED"** at the end: numbers for every topic.

The desk keeps watching the folder: drop a new `.txt` email in it and it is answered within a few seconds.
Emails already answered are skipped (listed in `output/processed_emails.txt`; delete that file to answer them again).
Replies go to `outbox/`. Stop with **Ctrl + C**.

**See the graphs any time:**
```powershell
uv run main.py graph     # opens output/langgraph_graphs.html (and saves PNGs when online)
```
A picture of both graphs is also in `docs/langgraph_graphs.png`.

**End of day:**
```powershell
uv run main.py report    # -> output/eod_compliance_report.md
uv run main.py eval      # -> scores in the terminal + experiments in LangSmith
```

## Folders and files

| Path | Purpose |
|------|---------|
| `outbox/` | Reply emails written by the desk |
| `output/` | `tickets.jsonl`, `grants_audit_log.json`, `processed_emails.txt`, `eod_compliance_report.md` |
| `sample_emails/` | 5 example emails (use it as the mail folder, or make your own folder) |
| `employees.json` | Employee directory |
| `it_security_policy.md` | Company policy used by RAG |
| `incoming_requests.json` | Same sample emails, used by the notebook |

Email file format:
```
From: divya.pillai@acme.com
Subject: Read access to prod-db

Hi team, I need read access to prod-db for 48 hours to debug INC-4412.
```
