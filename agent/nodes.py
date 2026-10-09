import re

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from agent.state import RefactorState

from agent.sandbox import run_tests
from pathlib import Path

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
5. Test plan: specific pytest test cases, including edge cases.

   Be concise. Use markdown headings for each section.
   Keep the test plan to at most 15 focused tests."""


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


CODER_PROMPT = """You are a senior Python engineer implementing a refactoring plan.

Produce exactly two files:
1. refactored.py: the refactored module, following the plan exactly.
2. test_refactored.py: pytest tests implementing the plan's test plan.
   Tests must import the module with `import refactored` and/or
   `from refactored import ...`.

Rules:
- Use only the Python standard library and pytest.
- No file, network, or subprocess access in the code or tests.
- Preserve every behavior listed under "Behavior to preserve".

If you are given previous failures: decide whether the bug is in the code
or in the test by checking against the plan. Fix whichever is wrong.
Never weaken or delete a test just to make it pass. Do not repeat a fix
that already failed.

Respond with ONLY these two blocks, raw Python inside, no markdown fences:
<refactored_code>
...
</refactored_code>
<test_code>
...
</test_code>"""


def extract_tag(text: str, tag: str) -> str:
    """Pull the contents of <tag>...</tag> out of the model's response."""
    match = re.search(rf"<{tag}>\s*(.*?)\s*</{tag}>", text, re.DOTALL)
    if not match:
        raise ValueError(f"Coder response missing <{tag}> block")
    code = match.group(1).strip()
    # Strip ``` fences in case the model added them anyway
    code = re.sub(r"^```(?:python)?\s*\n|\n?```$", "", code)
    return code + "\n"


def coder(state: RefactorState) -> dict:
    parts = [
        f"## Refactoring plan\n{state['plan']}",
        f"## Legacy module\n```python\n{state['legacy_code']}\n```",
    ]

    if state.get("error_history"):
        history = "\n\n".join(
            f"### Attempt {i + 1} failure\n{err}"
            for i, err in enumerate(state["error_history"])
        )
        parts.append(
            "## Your previous attempt\n"
            f"<refactored_code>\n{state['refactored_code']}\n</refactored_code>\n"
            f"<test_code>\n{state['test_code']}\n</test_code>"
        )
        parts.append(f"## Failure history (do not repeat these mistakes)\n{history}")

    response = llm.invoke([
        SystemMessage(content=CODER_PROMPT),
        HumanMessage(content="\n\n".join(parts)),
    ])
    text = get_text(response)

    return {
        "refactored_code": extract_tag(text, "refactored_code"),
        "test_code": extract_tag(text, "test_code"),
        "attempts": state.get("attempts", 0) + 1,
    }


MAX_ERROR_CHARS = 4000


def qa(state: RefactorState) -> dict:
    passed, output = run_tests(state["refactored_code"], state["test_code"])

    update = {"test_output": output, "tests_passed": passed}

    if not passed:
        # Keep the end of the output, where pytest puts the failure summary
        update["error_history"] = [output[-MAX_ERROR_CHARS:]]

    return update

if __name__ == "__main__":
    state = {
        "legacy_code": Path("samples/legacy_inventory.py").read_text(),
        "error_history": [],
    }

    state.update(architect(state))
    print("Architect done.")

    state.update(coder(state))
    print(f"Coder done (attempt {state['attempts']}).")

    Path("workspace/refactored.py").write_text(state["refactored_code"])
    Path("workspace/test_refactored.py").write_text(state["test_code"])

    state.update(qa(state))
    print("PASSED" if state["tests_passed"] else "FAILED")
    print(state["test_output"])