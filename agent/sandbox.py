import tempfile
from pathlib import Path

import docker

IMAGE = "refactor-sandbox"
TIMEOUT_SECONDS = 60


def run_tests(code: str, tests: str) -> tuple[bool, str]:
    """Run tests against code inside an isolated container.
    Returns (passed, pytest_output)."""
    client = docker.from_env()

    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "refactored.py").write_text(code)
        Path(tmp, "test_refactored.py").write_text(tests)

        container = client.containers.run(
            IMAGE,
            command="python -m pytest -q --tb=short -p no:cacheprovider",
            volumes={tmp: {"bind": "/app", "mode": "ro"}},
            environment={"PYTHONDONTWRITEBYTECODE": "1"},
            network_disabled=True,
            mem_limit="256m",
            detach=True,
        )

        try:
            result = container.wait(timeout=TIMEOUT_SECONDS)
            output = container.logs().decode()
            passed = result["StatusCode"] == 0
        except Exception:
            container.kill()
            output = f"Tests timed out after {TIMEOUT_SECONDS}s (possible infinite loop)"
            passed = False
        finally:
            container.remove(force=True)

    return passed, output


if __name__ == "__main__":
    good_code = "def add(a, b):\n    return a + b\n"
    bad_code = "def add(a, b):\n    return a - b\n"
    tests = "from refactored import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"

    print("GOOD:", run_tests(good_code, tests))
    print("BAD:", run_tests(bad_code, tests))