from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from agent.state import RefactorState

load_dotenv()

llm = ChatAnthropic(model="claude-sonnet-5-5", max_tokens=16000)


ARCHITECT_PROMPT = """You are a senior Python software architect.
You will receive a legacy Python module. Produce a refactoring plan that
another engineer will implement. Do NOT write the implementation.

Your plan must have these sections:

1. Code smells: each problem found, with one line on why it matters.
2. Target design: class/function names, method signatures, and what each
   is responsible for. The refactored code will live in ONE file named
   refactored.py.
3. Behavior to preserve: every observable behavior of the original,
   including edge cases (e.g. what happens when removing a missing item).
   The refactor must NOT change behavior unless listed under Improvements.
4. Improvements: any intentional behavior changes, each justified.
   Keep these minimal.
5. Test plan: specific pytest test cases, including edge cases. Be concise. 
    Use markdown headings for each section. Keep the test plan to at most 15 focused tests."""


def get_text(response) -> str:
    """Keep only the text blocks, dropping the model's thinking blocks."""
    if isinstance(response.content, str):
        return response.content
    return "".join(
        block["text"] for block in response.content if block.get("type") == "text"
    )


def architect(state: RefactorState) -> dict:
    messages = [
        SystemMessage(content=ARCHITECT_PROMPT),
        HumanMessage(content=f"Legacy module:\n```python\n{state['legacy_code']}\n```"),
    ]
    response = llm.invoke(messages)
    return {"plan": get_text(response)}


if __name__ == "__main__":
    with open("samples/legacy_inventory.py") as f:
        legacy = f.read()
    result = architect({"legacy_code": legacy})
    print(result["plan"])