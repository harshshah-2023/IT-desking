"""Topic: LLM Evaluation - LangSmith evaluate() on both RAG systems."""
from pydantic import BaseModel
from langsmith import Client, evaluate
from app.config import llm
from app.rag import vector_rag, vectorless_rag

DATASET = "it-policy-qa"
EXAMPLES = [
    ("What is the minimum password length?", "14 characters"),
    ("How long may a just-in-time privileged session last?", "At most 8 hours"),
    ("How often are privileged accounts re-certified?", "Monthly"),
    ("Can a contractor get admin access to aws-prod?", "No, contractors may never hold write or admin access to Restricted systems"),
]


class Grade(BaseModel):
    correct: bool


def correctness(inputs, outputs, reference_outputs):
    grade = llm.with_structured_output(Grade).invoke(
        f"Question: {inputs['question']}\nReference answer: {reference_outputs['answer']}\n"
        f"Student answer: {outputs['answer']}\nIs the student answer correct?")
    return grade.correct


def run_evals():
    client = Client()
    if not client.has_dataset(dataset_name=DATASET):
        dataset = client.create_dataset(dataset_name=DATASET)
        client.create_examples(dataset_id=dataset.id, examples=[
            {"inputs": {"question": q}, "outputs": {"answer": a}} for q, a in EXAMPLES])

    print("   [LLM Evaluation] dataset:", DATASET, f"({len(EXAMPLES)} questions)")
    for name, rag in [("vector-rag", vector_rag), ("vectorless-rag", vectorless_rag)]:
        results = evaluate(lambda inputs: {"answer": rag(inputs["question"])},
                           data=DATASET, evaluators=[correctness], experiment_prefix=name)
        df = results.to_pandas()
        score = df["feedback.correctness"].mean()
        print(f"   [LLM Evaluation] {name:15s} correctness = {score:.0%}")
    print("Open smith.langchain.com to compare the two experiments.")
