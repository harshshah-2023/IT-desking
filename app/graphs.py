"""Shows the LangGraph graphs: ASCII in the terminal, plus pictures in output/."""
import html
import re
import webbrowser
from app.config import OUTPUT

HTML = """<!doctype html><html><head><meta charset="utf-8"><title>LangGraph graphs</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"></script>
<style>body{{font-family:sans-serif;margin:24px}} .box{{border:1px solid #ccc;padding:16px;margin:16px 0;border-radius:8px}}</style>
</head><body>
<h1>IT Triage Desk - LangGraph graphs</h1>
<div class="box"><h2>1. Email workflow (app/pipeline.py)</h2><pre class="mermaid">{email}</pre></div>
<div class="box"><h2>2. Desk agent inside the 'desk' node (create_agent + middleware)</h2><pre class="mermaid">{desk}</pre></div>
<script>mermaid.initialize({{startOnLoad:true}});</script>
</body></html>"""


def clean_mermaid(text: str) -> str:
    """Make LangGraph's mermaid text safe for the browser (node ids with '.', '[' and ']')."""
    text = text.replace("\\2e", "_").replace("\\5b", "_").replace("\\5d", "_")
    return re.sub(r'^(\t\w+)\((?!\[)(.*)\)$', lambda m: f'{m.group(1)}["{m.group(2)}"]', text, flags=re.M)


def print_email_graph(email_graph):
    print("LangGraph email workflow:")
    try:
        print(email_graph.get_graph().draw_ascii())
    except ImportError:
        print("START -> extract -> desk -> reply -> END   (extract -> reply when blocked)")


def save_graphs(email_graph, desk, open_browser=False, png=False):
    """Save output/langgraph_graphs.html (+ PNG files when png=True and mermaid.ink is reachable)."""
    html_file = OUTPUT / "langgraph_graphs.html"
    html_file.write_text(HTML.format(email=html.escape(clean_mermaid(email_graph.get_graph().draw_mermaid())),
                                     desk=html.escape(clean_mermaid(desk.get_graph().draw_mermaid()))), encoding="utf-8")
    print(f"Graph page saved: {html_file}")
    for name, graph in ([("email_workflow", email_graph), ("desk_agent", desk)] if png else []):
        try:
            (OUTPUT / f"{name}.png").write_bytes(graph.get_graph().draw_mermaid_png())
            print(f"Graph image saved: {OUTPUT / (name + '.png')}")
        except Exception:
            pass   # PNG needs internet (mermaid.ink); the HTML page is enough
    if open_browser:
        webbrowser.open(html_file.as_uri())
