"""Topic: RAG - Vector RAG (FAISS) and Vectorless RAG (PageIndex idea)."""
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from app.config import llm, POLICY_FILE
from app.log import show, STATS, CURRENT

policy = POLICY_FILE.read_text(encoding="utf-8")
sections = MarkdownHeaderTextSplitter([("##", "chapter"), ("###", "section")]).split_text(policy)


def answer_from(context: str, question: str) -> str:
    prompt = (f"Answer ONLY from this context. If the answer is not there, say \"I don't know\".\n\n"
              f"{context}\n\nQuestion: {question}")
    return llm.invoke(prompt).content


# ---------------- Vector RAG ----------------
_vector_store = None

def vector_rag(question: str) -> str:
    global _vector_store
    if _vector_store is None:   # build the FAISS index the first time it is needed
        chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_documents(sections)
        _vector_store = FAISS.from_documents(chunks, OpenAIEmbeddings(model="text-embedding-3-small"))
    docs = _vector_store.similarity_search(question, k=3)
    show("Vector RAG", f"FAISS found {len(docs)} chunks for: {question}")
    return answer_from("\n\n".join(d.page_content for d in docs), question)


# ---------------- Vectorless RAG ----------------
nodes = [{"node_id": str(i),
          "title": s.metadata.get("section", s.metadata.get("chapter", "General")),
          "text": s.page_content} for i, s in enumerate(sections)]
table_of_contents = "\n".join(f"{n['node_id']}: {n['title']} - {n['text'][:100]}" for n in nodes)


class TreeSearch(BaseModel):
    thinking: str = Field(description="Why these sections were chosen")
    node_list: list[str] = Field(description="node_ids of the sections that answer the question")


def vectorless_rag(question: str) -> str:
    search = llm.with_structured_output(TreeSearch).invoke(
        f"Question: {question}\n\nDocument sections:\n{table_of_contents}\n\nWhich node_ids contain the answer?")
    chosen = [n for n in nodes if n["node_id"] in search.node_list]
    if not chosen:          # LLM picked nothing -> read the whole (short) policy instead of guessing
        chosen = nodes
    STATS["rag_searches"] += 1
    show("Vectorless RAG", f"Q: {question}")
    show("Vectorless RAG", f"LLM picked sections: {[n['title'] for n in chosen]}")
    show("Vectorless RAG", f"Why: {search.thinking[:150]}")
    answer = answer_from("\n\n".join(n["text"] for n in chosen), question)
    show("Vectorless RAG", f"Answer: {answer[:150]}")
    return answer


@tool
def search_policy(question: str) -> str:
    """Search the IT security policy for rules and time limits."""
    STATS["tool_calls"] += 1
    CURRENT["tools"].append("search_policy")
    show("Tools", f"search_policy({question})")
    return vectorless_rag(question)
