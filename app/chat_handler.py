from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agents import (
    AgentState,
    scrape_agent,
    profile_analysis_agent,
    job_fit_agent,
    content_enhancement_agent,
    skill_gap_agent,
    route_agent,
)


class ChatHandler:
    def __init__(self):
        self.memory = MemorySaver()
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("scrape", scrape_agent)
        workflow.add_node("profile_analysis", profile_analysis_agent)
        workflow.add_node("job_fit", job_fit_agent)
        workflow.add_node("content_enhancement", content_enhancement_agent)
        workflow.add_node("skill_gap", skill_gap_agent)

        workflow.add_conditional_edges(
            "scrape",
            lambda state: state.get("next_node", "profile_analysis"),
            {
                "profile_analysis": "profile_analysis",
                "job_fit": "job_fit",
                "content_enhancement": "content_enhancement",
                "skill_gap": "skill_gap"
            }
        )

        workflow.add_edge("profile_analysis", END)
        workflow.add_edge("job_fit", END)
        workflow.add_edge("content_enhancement", END)
        workflow.add_edge("skill_gap", END)

        workflow.set_entry_point("scrape")
        return workflow.compile(checkpointer=self.memory)

    def handle_chat(self, profile_url: str, user_query: str, session_id: str):
        try:
            previous_state = self.memory.get(session_id) or {}

            state = {
                "profile_url": profile_url,
                "profile_data": previous_state.get("profile_data"),
                "user_query": user_query,
                "job_role": previous_state.get("job_role"),
                "analysis_result": None,
                "session_id": session_id,
                "chat_history": previous_state.get("chat_history", []),
                "next_node": None
            }

            config = {"configurable": {"thread_id": session_id}}
            result = self.workflow.invoke(state, config=config)

            if isinstance(result, dict) and "analysis_result" in result:
                return result["analysis_result"]
            elif isinstance(result, str):
                return result
            else:
                return "Error: Unexpected result from AI workflow."

        except Exception as e:
            print(f"Chat error: {e}")
            return f"Unexpected error: {str(e)}"
