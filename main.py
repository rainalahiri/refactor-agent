import sys
from pathlib import Path

from agent.graph import build_graph


def main():
    source = Path(sys.argv[1] if len(sys.argv) > 1 else "samples/legacy_inventory.py")

    app = build_graph()
    initial_state = {
        "legacy_code": source.read_text(),
        "attempts": 0,
        "error_history": [],
    }

    final = {}
    for step in app.stream(initial_state, stream_mode="updates"):
        for node, update in step.items():
            final.update(update)
            if node == "qa":
                status = "PASSED" if update["tests_passed"] else "FAILED"
                print(f"[qa] attempt {final['attempts']}: {status}")
            else:
                print(f"[{node}] done")

    out = Path("workspace")
    out.mkdir(exist_ok=True)
    (out / "refactored.py").write_text(final["refactored_code"])
    (out / "test_refactored.py").write_text(final["test_code"])
    (out / "plan.md").write_text(final["plan"])

    if final["tests_passed"]:
        print(f"\nSuccess after {final['attempts']} attempt(s). Output in workspace/")
    else:
        print(f"\nGave up after {final['attempts']} attempts. Last output:\n{final['test_output']}")


if __name__ == "__main__":
    main()