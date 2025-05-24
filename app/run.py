#!/usr/bin/env python3
import sys
import os
import subprocess
from dotenv import load_dotenv

def main():
    # Load environment variables from .env file in current directory
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

    # Define required environment variables
    required_vars = ['HUGGING_FACE_API_KEY', 'APIFY_API_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Missing environment variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file")
        sys.exit(1)

    # Run Streamlit app
    subprocess.run([
        "streamlit", "run", "app/main.py",
        "--server.port", "8501",
        "--server.address", "0.0.0.0"
    ])

if __name__ == "__main__":
    main()
