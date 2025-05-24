LinkedIn AI Optimizer
An AI-powered chat system to optimize LinkedIn profiles, analyze job fit, and provide career guidance. Built with Streamlit, LangGraph, and Apify for a seamless, personalized experience.
Features

Interactive Chat Interface: Input a LinkedIn profile URL and job role to get feedback and recommendations.
Profile Analysis: Evaluates LinkedIn profile sections (About, Experience, Skills) for gaps and improvements.
Job Fit Analysis: Compares profiles to job descriptions and generates a match score.
Content Enhancement: Rewrites profile sections to align with industry standards.
Career Guidance: Suggests skills and learning resources for career growth.
Memory System: Retains user context across sessions using LangGraph.

Setup

Clone the repo: git clone https://github.com/<your-username>/linkedin-ai-optimizer.git
Install dependencies: pip install -r requirements.txt
Install Ollama and pull Mistral: ollama pull mistral
Set environment variable:
APIFY_API_TOKEN: Your Apify API key.


Run the app: streamlit run app/main.py

Deployment
Hosted on Streamlit Cloud at <your-public-url>.
Requirements
See requirements.txt for dependencies.
Documentation

docs/architecture.md: System design, challenges, and solutions.
docs/setup.md: Detailed setup instructions.

