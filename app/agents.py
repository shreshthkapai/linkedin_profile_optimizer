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
    """
    Typed dict for storing the state of the profile optimizer agent.

    Fields:
        profile_url: LinkedIn profile URL to be analyzed.
        profile_data: Fetched data from the LinkedIn profile.
        user_query: The user's question or command.
        job_role: Optional target job role.
        analysis_result: Latest result from agent analysis.
        session_id: Session identifier for continuity.
        chat_history: Chronological list of user/assistant message dicts.
        next_node: Which agent to call next in the workflow.
    """
    ...

def truncate_chat_history(chat_history: List[Dict[str, str]], max_turns=10) -> List[Dict[str, str]]:
    """
    Limit chat history to the most recent exchanges (default: 10 user/assistant pairs).

    This ensures prompts don't grow too large for the LLM context window.
    """
    if len(chat_history) <= max_turns * 2:
        return chat_history
    # Only keep the latest max_turns pairs (each turn is 2 messages).
    return chat_history[-max_turns * 2:]

def call_llm_api(messages: List[Dict[str, str]]) -> str:
    """
    Query the HuggingFace LLM API with formatted prompt and return its response.

    Args:
        messages: List of message dicts, each with 'role' and 'content'.

    Returns:
        Cleaned string response from the LLM.
    """
    hf_token = os.getenv('HUGGING_FACE_API_KEY')
    if not hf_token:
        raise ValueError("HUGGING_FACE_API_KEY not configured.")

    client = InferenceClient(token=hf_token)

    try:
        # Format messages for the LLM: role-dependent prompt construction.
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

        result = response.strip() if isinstance(response, str) else str(response).strip()

        # Remove short or empty lines from the response for clarity.
        lines = [line.strip() for line in result.split('\n') if line.strip()]
        cleaned_lines = [line for line in lines if len(line) > 5]
        return '\n\n'.join(cleaned_lines) if cleaned_lines else result

    except Exception as e:
        print(f"LLM API Error: {str(e)}")
        return "I apologize, but I'm having trouble processing your request right now. Please try again."

def scrape_agent(state: AgentState) -> AgentState:
    """
    Populate profile_data in the agent state by scraping the LinkedIn profile if not already set.
    """
    if not state.get("profile_data"):
        profile_data = scrape_profile(state["profile_url"])
        state["profile_data"] = profile_data
    return state

def profile_analysis_agent(state: AgentState) -> AgentState:
    """
    Generate a LinkedIn profile analysis using the profile_analysis_prompt.
    """
    return _run_agent_with_prompt(state, profile_analysis_prompt)

def job_fit_agent(state: AgentState) -> AgentState:
    """
    Assess job fit for a given profile and job role using the job_fit_prompt.
    """
    return _run_agent_with_prompt(state, job_fit_prompt)

def content_enhancement_agent(state: AgentState) -> AgentState:
    """
    Suggest content improvements for a profile using the content_enhancement_prompt.
    """
    return _run_agent_with_prompt(state, content_enhancement_prompt)

def skill_gap_agent(state: AgentState) -> AgentState:
    """
    Identify skill gaps for a profile compared to a target job using the skill_gap_prompt.
    """
    return _run_agent_with_prompt(state, skill_gap_prompt)

def _run_agent_with_prompt(state: AgentState, prompt_template: str) -> AgentState:
    """
    Helper for all agent flows: formats prompts, calls LLM, updates state with results and chat history.

    Args:
        state: Current agent state.
        prompt_template: Prompt string with placeholders to fill.

    Returns:
        Updated agent state.
    """
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
    """
    Convert raw LinkedIn profile data into a readable summary for LLM prompts.

    Shows name, headline, summary, up to 3 experiences, and up to 10 skills.
    """
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
        # Only show up to 3 most recent experiences.
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
    """
    Clean and validate the LLM's response.
    - Appends match scores if present.
    - Rejects overly short responses.
    """
    if not response or not isinstance(response, str):
        return "Sorry, the assistant could not generate a valid response."

    match_scores = re.findall(r"\b\d{1,3}%\b", response)
    if "match" in response.lower() and match_scores:
        response += f"\n\n✅ Parsed Match Scores: {', '.join(match_scores)}"

    if len(response.strip()) < 50:
        return "Sorry, the assistant's response was too short. Please ask your question again or provide more detail."

    return response

def route_agent(state: AgentState) -> AgentState:
    """
    Analyze user query and set 'next_node' in state to route flow to the appropriate agent.

    Routing is keyword-based; defaults to profile_analysis if no match.
    """
    try:
        user_query = state['user_query'].lower()
        # Order of checks matters—first match wins.
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
