import streamlit as st

st.set_page_config(page_title="LearnTube", page_icon="💼", layout="wide")

import uuid
import os
from chat_handler import ChatHandler

# Load secrets from Streamlit or .env (fallback for local dev)
try:
    if hasattr(st, 'secrets') and st.secrets:
        os.environ['HUGGING_FACE_API_KEY'] = st.secrets.get('HUGGING_FACE_API_KEY', os.getenv('HUGGING_FACE_API_KEY', ''))
        os.environ['APIFY_API_TOKEN'] = st.secrets.get('APIFY_API_TOKEN', os.getenv('APIFY_API_TOKEN', ''))
        os.environ['LI_AT_COOKIE'] = st.secrets.get('LI_AT_COOKIE', os.getenv('LI_AT_COOKIE', ''))
except Exception:
    from dotenv import load_dotenv
    load_dotenv()

# Initialize Streamlit session state variables if not already set
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "chat_handler" not in st.session_state:
    st.session_state.chat_handler = ChatHandler()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "profile_url" not in st.session_state:
    st.session_state.profile_url = ""

def main():
    """
    Main function to render the Streamlit web app UI for the LinkedIn Profile Optimizer.
    Handles user input, loads profile, manages chat messages, and displays interaction interface.
    """
    st.title("🚀 LearnTube - LinkedIn Profile Optimizer")
    st.markdown("*by CareerNinja*")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        profile_url = st.text_input(
            "LinkedIn Profile URL:", 
            value=st.session_state.profile_url,
            placeholder="https://www.linkedin.com/in/your-profile"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Load Profile", type="primary"):
            if profile_url:
                st.session_state.profile_url = profile_url
                st.session_state.messages = []
                st.success("Profile loaded! Start chatting below.")
                st.rerun()  # Forces Streamlit to reload UI with new state
    
    if st.session_state.profile_url:
        st.markdown("---")
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Wait for user input in chat, then generate assistant reply
        if prompt := st.chat_input("Ask about your profile, job fit, career guidance..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Analyzing your profile..."):
                    response = st.session_state.chat_handler.handle_chat(
                        profile_url=st.session_state.profile_url,
                        user_query=prompt,
                        session_id=st.session_state.session_id
                    )
                    
                    if response:
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    else:
                        error_msg = "⚠️ Unable to process request. Please try again or check your LinkedIn URL."
                        st.markdown(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
    else:
        st.info("👆 Enter your LinkedIn profile URL above to start chatting with the AI assistant.")
        
        # Example prompts to guide new users
        st.markdown("### 💡 Example Questions:")
        st.markdown("""
        - "Analyze my LinkedIn profile and suggest improvements"
        - "How well does my profile match a Software Engineer role?"
        - "Rewrite my About section for better impact"
        - "What skills am I missing for a Data Scientist position?"
        - "Give me career guidance for transitioning to Product Management"
        """)

if __name__ == "__main__":
    main()
