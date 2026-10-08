from typing import TypedDict, Annotated
import operator


class RefactorState(TypedDict):
    # --- input ---
    legacy_code: str          # the messy file we're refactoring

    # --- Architect writes ---
    plan: str                 # step-by-step refactoring plan

    # --- Coder writes ---
    refactored_code: str      # the new clean module
    test_code: str            # pytest tests for it

    # --- QA writes ---
    test_output: str          # raw pytest output from the container
    tests_passed: bool        # did everything pass?

    # --- loop control ---
    attempts: int             # how many Coder→QA rounds so far
    error_history: Annotated[list[str], operator.add]  # every failure, kept forever