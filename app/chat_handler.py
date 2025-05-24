from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agents import AgentState, smart_analysis_node

class ChatHandler:
    def __init__(self):
        self.memory = MemorySaver()
        self.workflow = self._build_workflow()
        
    def _build_workflow(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("analyze", smart_analysis_node)
        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", END)
        return workflow.compile(checkpointer=self.memory)
    
    def handle_chat(self, profile_url: str, user_query: str, session_id: str):
        try:
            state = {
                "profile_url": profile_url,
                "profile_data": None,
                "user_query": user_query,
                "job_role": None,
                "analysis_result": None,
                "session_id": session_id
            }
            
            config = {"configurable": {"thread_id": session_id}}
            result = self.workflow.invoke(state, config=config)
            return result.get("analysis_result")
            
        except Exception as e:
            print(f"Chat error: {e}")
            return None