from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from huggingface_hub import InferenceClient
from typing import TypedDict, Optional
from prompts import dynamic_analysis_prompt
from scraper import scrape_profile
import requests
import os

class AgentState(TypedDict):
    profile_url: str
    profile_data: Optional[dict]
    user_query: str
    job_role: Optional[str]
    analysis_result: Optional[str]
    session_id: str

def call_llm_api(prompt: str) -> str:
    hf_token = os.getenv('HUGGING_FACE_API_KEY')
    if not hf_token:
        return "Error: HUGGING_FACE_API_KEY not configured."

    try:
        client = InferenceClient(
            model="mistralai/Mistral-7B-Instruct-v0.3",
            token=hf_token
        )

        completion = client.chat.completions.create(
            model="mistralai/Mistral-7B-Instruct-v0.3",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.6,
        )

        return completion.choices[0].message.content.strip()

    except Exception as e:
        print(f"An unexpected error occurred in call_llm_api: {e}")
        return f"Error: An unexpected issue occurred. {str(e)[:200]}"
    
def smart_analysis_node(state: AgentState) -> AgentState:
    if not state.get("profile_data"):
        profile_data = scrape_profile(state["profile_url"])
        state["profile_data"] = profile_data
    else:
        profile_data = state["profile_data"]

    if not profile_data:
        state["analysis_result"] = "Unable to fetch profile data. Please check your LinkedIn URL."
        return state

    prompt = dynamic_analysis_prompt.format(
        profile_data=profile_data,
        user_query=state["user_query"],
        job_role=state.get("job_role", "")
    )

    result = call_llm_api(prompt)
    state["analysis_result"] = result
    return state