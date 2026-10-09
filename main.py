import argparse
from pathlib import Path

from agent.graph import build_graph


def main():
    parser = argparse.ArgumentParser(description="Multi-agent refactoring pipeline")
    parser.add_argument("source", nargs="?", default="samples/legacy_inventory.py")
    parser.add_argument("--inject-bug", action="store_true",
                        help="Demo: sabotage the first attempt to show self-correction")
    args = parser.parse_args()

    source = Path(args.source)
    app = build_graph()
    initial_state = {
        "legacy_code": source.read_text(encoding="utf-8"),
        "attempts": 0,
        "error_history": [],
        "inject_bug": args.inject_bug,
    }

    final = {}
    for step in app.stream(initial_state, stream_mode="updates"):
        for node, update in step.items():
            final.update(update)
            if node == "qa":
                status = "PASSED" if update["tests_passed"] else "FAILED"
                print(f"[qa] attempt {final['attempts']}: {status}")
                if not update["tests_passed"]:
                    for line in update["test_output"].splitlines():
                        if line.startswith("FAILED"):
                            print(f"     {line}")
            else:
                print(f"[{node}] done")

    out = Path("workspace") / source.stem
    out.mkdir(parents=True, exist_ok=True)
    (out / "refactored.py").write_text(final["refactored_code"], encoding="utf-8")
    (out / "test_refactored.py").write_text(final["test_code"], encoding="utf-8")
    (out / "plan.md").write_text(final["plan"], encoding="utf-8")
    (out / "result.txt").write_text(
        f"passed: {final['tests_passed']}\nattempts: {final['attempts']}\n",
        encoding="utf-8",
    )

    if final["tests_passed"]:
        print(f"\nSuccess after {final['attempts']} attempt(s). Output in {out}/")
    else:
        print(f"\nGave up after {final['attempts']} attempts. Last output:\n{final['test_output']}")


if __name__ == "__main__":
    main()