from langgraph.graph import StateGraph, START, END

from agent.state import RefactorState
from agent.nodes import architect, coder, qa

MAX_ATTEMPTS = 3


def route_after_qa(state: RefactorState) -> str:
    """Decide what happens after tests run."""
    if state["tests_passed"]:
        return "done"
    if state["attempts"] >= MAX_ATTEMPTS:
        return "give_up"
    return "retry"


def build_graph():
    graph = StateGraph(RefactorState)

    graph.add_node("architect", architect)
    graph.add_node("coder", coder)
    graph.add_node("qa", qa)

    graph.add_edge(START, "architect")
    graph.add_edge("architect", "coder")
    graph.add_edge("coder", "qa")

    graph.add_conditional_edges(
        "qa",
        route_after_qa,
        {"done": END, "give_up": END, "retry": "coder"},
    )

    return graph.compile()