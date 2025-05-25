from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from huggingface_hub import InferenceClient
from typing import TypedDict, Optional, List, Dict
from prompts import (
    profile_analysis_prompt,
    job_fit_prompt,
    content_enhancement_prompt,
    skill_gap_prompt,
)
from scraper import scrape_profile
import os


class AgentState(TypedDict):
    profile_url: str
    profile_data: Optional[dict]
    user_query: str
    job_role: Optional[str]
    analysis_result: Optional[str]
    session_id: str
    chat_history: List[Dict[str, str]]
    next_node: Optional[str]


def truncate_chat_history(chat_history: List[Dict[str, str]], max_turns=10) -> List[Dict[str, str]]:
    if len(chat_history) <= max_turns * 2:
        return chat_history
    return chat_history[-max_turns * 2:]


def call_llm_api(messages: List[Dict[str, str]]) -> str:
    hf_token = os.getenv('HUGGING_FACE_API_KEY')
    if not hf_token:
        raise ValueError("HUGGING_FACE_API_KEY not configured.")

    client = InferenceClient(
        model="mistralai/Mistral-7B-Instruct-v0.3",
        token=hf_token
    )

    try:
        completion = client.chat.completions.create(
            model="mistralai/Mistral-7B-Instruct-v0.3",
            messages=messages,
            max_tokens=2500,
            temperature=0.4,
            top_p=0.9,
            frequency_penalty=0.3,
            presence_penalty=0.1
        )
        
        # Handle response properly
        if hasattr(completion, 'choices') and len(completion.choices) > 0:
            if hasattr(completion.choices[0], 'message'):
                return completion.choices[0].message.content.strip()
            elif isinstance(completion.choices[0], dict):
                return completion.choices[0].get('message', {}).get('content', '').strip()
            else:
                return str(completion.choices[0]).strip()
        
        return str(completion).strip()

    except Exception as e:
        print(f"LLM API Error: {str(e)}")
        return "Error processing request"


def scrape_agent(state: AgentState) -> AgentState:
    if not state.get("profile_data"):
        profile_data = scrape_profile(state["profile_url"])
        state["profile_data"] = profile_data
    return state


def profile_analysis_agent(state: AgentState) -> AgentState:
    return _run_agent_with_prompt(state, profile_analysis_prompt)


def job_fit_agent(state: AgentState) -> AgentState:
    return _run_agent_with_prompt(state, job_fit_prompt)


def content_enhancement_agent(state: AgentState) -> AgentState:
    return _run_agent_with_prompt(state, content_enhancement_prompt)


def skill_gap_agent(state: AgentState) -> AgentState:
    return _run_agent_with_prompt(state, skill_gap_prompt)


def _run_agent_with_prompt(state: AgentState, prompt_template: str) -> AgentState:
    if not state.get("profile_data"):
        state["analysis_result"] = "Profile data missing. Cannot proceed."
        return state

    try:
        base_prompt = prompt_template.format(
            profile_data=state["profile_data"],
            user_query=state["user_query"],
            job_role=state.get("job_role", "")
        )

        system_msg = {"role": "system", "content": base_prompt}
        history = truncate_chat_history(state.get("chat_history", []))
        messages = [system_msg] + history + [{"role": "user", "content": state["user_query"]}]

        result = call_llm_api(messages)

        updated_history = history + [
            {"role": "user", "content": state["user_query"]},
            {"role": "assistant", "content": result}
        ]

        state["chat_history"] = updated_history
        state["analysis_result"] = result
        return state

    except Exception as e:
        state["analysis_result"] = f"Error during AI processing: {str(e)}"
        return state


def route_agent(state: AgentState) -> AgentState:
    try:
        routing_prompt = f"""
You are a smart router in a multi-agent AI system for LinkedIn career help.

Classify the user's message into one of these categories and respond ONLY with the category name:
- profile_analysis
- job_fit
- content_enhancement
- skill_gap

USER QUERY:
"{state['user_query']}"
""".strip()

        messages = [
            {"role": "system", "content": "You are a routing classifier."},
            {"role": "user", "content": routing_prompt}
        ]

        # Get and clean response
        response = call_llm_api(messages)
        cleaned = str(response).lower().strip()
        
        # Valid categories
        valid_categories = {
            "profile_analysis", 
            "job_fit", 
            "content_enhancement", 
            "skill_gap"
        }
        
        # Default to profile_analysis if response isn't valid
        state["next_node"] = cleaned if cleaned in valid_categories else "profile_analysis"
        return state

    except Exception as e:
        print(f"Routing error: {e}")
        state["next_node"] = "profile_analysis"
        return state
