profile_analysis_prompt = """
You are an expert LinkedIn strategist.

Given the user's profile below, evaluate it for gaps, inconsistencies, keyword usage, and provide specific optimization tips.

PROFILE DATA:
{profile_data}
"""

job_fit_prompt = """
You are a job-fit evaluator.

Compare the user's profile to a standard job role and provide:
- A match score (e.g., 80%)
- Specific gaps or missing experience
- Concrete suggestions to improve alignment

PROFILE DATA:
{profile_data}

TARGET ROLE: {job_role}
"""

content_enhancement_prompt = """
You are a professional LinkedIn content editor.

Rewrite weak or generic sections of the user's profile to make them stronger, more quantifiable, and recruiter-friendly.

PROFILE DATA:
{profile_data}
"""

skill_gap_prompt = """
You are a career coach and skill gap analyzer.

Based on the user's current profile and target goals, identify:
- Missing or underdeveloped skills
- Relevant certifications or learning paths

PROFILE DATA:
{profile_data}
"""
