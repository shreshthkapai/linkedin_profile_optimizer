# agents.py
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
import json
import re


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

    client = InferenceClient(token=hf_token)

    try:
        prompt_parts = []
        for msg in messages:
            if msg['role'] == 'system':
                prompt_parts.append(f"System: {msg['content']}")
            elif msg['role'] == 'user':
                prompt_parts.append(f"Human: {msg['content']}")
            elif msg['role'] == 'assistant':
                prompt_parts.append(f"Assistant: {msg['content']}")
        full_prompt = "\n\n".join(prompt_parts) + "\n\nAssistant:"
        
        response = client.text_generation(
            prompt=full_prompt,
            model="mistralai/Mistral-7B-Instruct-v0.3",
            max_new_tokens=1000,
            temperature=0.3,
            top_p=0.9,
            repetition_penalty=1.1,
            stop_sequences=["Human:", "System:"],
            return_full_text=False
        )

        if isinstance(response, str):
            result = response.strip()
        else:
            result = str(response).strip()

        lines = [line.strip() for line in result.split('\n') if line.strip()]
        cleaned_lines = [line for line in lines if len(line) > 5]
        return '\n\n'.join(cleaned_lines) if cleaned_lines else result

    except Exception as e:
        print(f"LLM API Error: {str(e)}")
        return "I apologize, but I'm having trouble processing your request right now. Please try again."


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
        profile_summary = _format_profile_data(state["profile_data"])
        base_prompt = prompt_template.format(
            profile_data=profile_summary,
            user_query=state["user_query"],
            job_role=state.get("job_role", "")
        )

        system_msg = {"role": "system", "content": base_prompt}
        history = truncate_chat_history(state.get("chat_history", []))
        messages = [system_msg] + history + [{"role": "user", "content": state["user_query"]}]

        result = call_llm_api(messages)
        validated_result = _validate_response(result)

        updated_history = history + [
            {"role": "user", "content": state["user_query"]},
            {"role": "assistant", "content": validated_result}
        ]

        state["chat_history"] = updated_history
        state["analysis_result"] = validated_result
        return state

    except Exception as e:
        state["analysis_result"] = f"Error during AI processing: {str(e)}"
        return state


def _format_profile_data(profile_data: dict) -> str:
    if not profile_data:
        return "Profile data not available"
    
    summary_parts = []

    if profile_data.get("name"):
        summary_parts.append(f"Name: {profile_data['name']}")
    if profile_data.get("headline"):
        summary_parts.append(f"Headline: {profile_data['headline']}")
    if profile_data.get("summary"):
        summary_parts.append(f"Summary: {profile_data['summary']}")
    if profile_data.get("experience"):
        summary_parts.append("Experience:")
        for exp in profile_data["experience"][:3]:
            if isinstance(exp, dict):
                title = exp.get("title", "")
                company = exp.get("company", "")
                summary_parts.append(f"  - {title} at {company}")
    if profile_data.get("skills"):
        skills_list = profile_data["skills"]
        if isinstance(skills_list, list) and skills_list:
            if isinstance(skills_list[0], dict):
                skills_names = [skill.get("name", "") for skill in skills_list[:10]]
            else:
                skills_names = skills_list[:10]
            summary_parts.append(f"Skills: {', '.join(str(s) for s in skills_names if s)}")
    return "\n".join(summary_parts) if summary_parts else "Limited profile information available"


def _validate_response(response: str) -> str:
    if not response or not isinstance(response, str):
        return "Sorry, the assistant could not generate a valid response."

    # Check if it contains a match score percentage
    match_scores = re.findall(r"\b\d{1,3}%\b", response)
    if "match" in response.lower() and match_scores:
        response += f"\n\n✅ Parsed Match Scores: {', '.join(match_scores)}"
    
    if len(response.strip()) < 50:
        return "Sorry, the assistant's response was too short. Please ask your question again or provide more detail."

    return response


def route_agent(state: AgentState) -> AgentState:
    try:
        user_query = state['user_query'].lower()
        if any(word in user_query for word in ['job', 'role', 'position', 'career', 'suited', 'fit']):
            state["next_node"] = "job_fit"
        elif any(word in user_query for word in ['improve', 'enhance', 'better', 'rewrite', 'content']):
            state["next_node"] = "content_enhancement"  
        elif any(word in user_query for word in ['skill', 'learn', 'gap', 'missing', 'development']):
            state["next_node"] = "skill_gap"
        else:
            state["next_node"] = "profile_analysis"
        return state
    except Exception as e:
        print(f"Routing error: {e}")
        state["next_node"] = "profile_analysis"
        return state
