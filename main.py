"""IT Access & Compliance Triage Desk.

  uv run main.py sample_emails   -> answer every email in that folder, then keep watching it
  uv run main.py                 -> asks you for the folder name
  uv run main.py graph           -> show the LangGraph graphs (opens in your browser)
  uv run main.py report          -> end-of-day compliance report (deep agent)
  uv run main.py eval            -> evaluate the RAG systems with LangSmith
"""
import sys
import time
from pathlib import Path

from app.config import ROOT, DONE_FILE
from app.log import show, STATS, CURRENT, start_email


def read_email(path):
    """Email file format:  From: ...  /  Subject: ...  /  blank line  /  body"""
    header, _, body = path.read_text(encoding="utf-8").partition("\n\n")
    fields = dict(line.split(":", 1) for line in header.splitlines() if ":" in line)
    return {"email_id": path.stem,
            "sender": fields.get("From", "unknown").strip(),
            "subject": fields.get("Subject", "(no subject)").strip(),
            "body": body.strip()}


def run_one_email(email_graph, email):
    """Run the LangGraph workflow and print every node as it finishes."""
    start_email()
    state = dict(email)
    for update in email_graph.stream(email, stream_mode="updates"):
        for node, values in update.items():
            CURRENT["path"].append(node)
            state.update(values or {})
            show("LangGraph", f"node '{node}' finished")
    CURRENT["path"].append("END")

    t = state.get("ticket")
    print(f"\n   ---------- Summary for {email['email_id']} ----------")
    print(f"   Graph path : {' -> '.join(CURRENT['path'])}")
    print(f"   Ticket     : {'BLOCKED by guardrail' if t is None else t['request_type'] + ' | ' + str(t['system']) + ' | ' + t['access_level']}")
    print(f"   Tools used : {', '.join(CURRENT['tools']) or 'none'}")
    print(f"   Approval   : {', '.join(CURRENT['decisions']) or 'not needed'}")
    print(f"   Reply file : outbox/{email['email_id']}_reply.txt")
    print(f"\n   REPLY EMAIL:\n   " + state["reply"].replace("\n", "\n   ") + "\n")


def workflow_summary(folder):
    s = STATS
    types = ", ".join(f"{k}={v}" for k, v in s["types"].items()) or "none"
    print("\n" + "#" * 70)
    print("HOW YOUR WORKFLOW WORKED")
    print("#" * 70)
    print(f"""
 1. Input            : main.py read {s['emails']} email(s) from {folder}
 2. LangGraph        : each email ran through email_graph
                       START -> extract -> desk -> reply -> END  (blocked: extract -> reply)
 3. Guardrails       : PII hidden in {s['pii_hidden']} email(s), {s['blocked']} prompt injection(s) blocked
 4. Structured Output: emails turned into Tickets ({types})
 5. Desk Agent       : create_agent ReAct loop made {s['tool_calls']} tool call(s), memory per sender (MemorySaver)
 6. Vectorless RAG   : {s['rag_searches']} policy search(es) - LLM picked policy sections, no embeddings
 7. Human-in-the-Loop: approved={s['approve']}, edited={s['edit']}, rejected={s['reject']}
 8. LLM Gateway      : LiteLLM wrote the replies | models={', '.join(s['models']) or 'none'} | cost=${s['cost']:.6f}
 9. Output           : {s['replies']} reply email(s) in outbox/, grants in output/grants_audit_log.json

 Next: uv run main.py report  -> Deep Agents writes the end-of-day compliance report
       uv run main.py eval    -> LangSmith compares Vector RAG (FAISS) vs Vectorless RAG
       uv run main.py graph   -> see the LangGraph graphs in your browser
""")


def process_folder(folder_name):
    from app.pipeline import email_graph
    from app.desk import desk
    from app.graphs import print_email_graph, save_graphs

    folder = Path(folder_name)
    if not folder.is_absolute():
        folder = ROOT / folder
    if not folder.is_dir():
        print(f"Folder not found: {folder}")
        return

    print_email_graph(email_graph)
    save_graphs(email_graph, desk)
    print("Open it in your browser, or run:  uv run main.py graph")

    done = set(DONE_FILE.read_text(encoding="utf-8").splitlines()) if DONE_FILE.exists() else set()
    print(f"\nReading emails from {folder} ... (Ctrl+C to stop)\n")

    try:
        while True:
            new_emails = 0
            for path in sorted(folder.glob("*.txt")):
                key = str(path.resolve())
                if key in done:
                    continue                         # already answered
                if not path.read_text(encoding="utf-8").lstrip().startswith("From:"):
                    done.add(key)                    # not an email (no "From:" line) -> ignore it
                    print(f"Skipped {path.name}: not an email (it must start with 'From:')")
                    continue
                email = read_email(path)
                print("=" * 70)
                print(f"NEW EMAIL {email['email_id']} from {email['sender']}: {email['subject']}")
                print("=" * 70)
                run_one_email(email_graph, email)
                new_emails += 1
                done.add(key)
                with open(DONE_FILE, "a", encoding="utf-8") as f:
                    f.write(key + "\n")
            if new_emails:
                workflow_summary(folder)
                print("Watching for new emails... (Ctrl+C to stop)")
            time.sleep(3)
    except KeyboardInterrupt:
        print("\nStopped.")
        if STATS["emails"] == 0:
            print("No new emails were found. To answer the same emails again, delete output/processed_emails.txt")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else input("Enter the mail folder name [sample_emails]: ").strip()
    arg = arg or "sample_emails"          # just pressing Enter uses the sample emails
    if arg == "report":
        from app.report import make_report
        make_report()
    elif arg == "eval":
        from app.evals import run_evals
        run_evals()
    elif arg == "graph":
        from app.pipeline import email_graph
        from app.desk import desk
        from app.graphs import print_email_graph, save_graphs
        print_email_graph(email_graph)
        save_graphs(email_graph, desk, open_browser=True, png=True)
    else:
        process_folder(arg)
