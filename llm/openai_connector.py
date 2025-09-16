# Configuration of our OpenAI chat model (LLM) connection for the entire app.
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI # Integration OpenAI with LangChain pipelines.

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # Fetch our OpenAI key from env file
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in the environment.")

def get_llm():
    llm = ChatOpenAI(
        model=MODEL_NAME,
        temperature=0.3, # low temperature = more deterministic (good for insights, intent classification).
        api_key=OPENAI_API_KEY,
        request_timeout=60
    )
    return llm # Return llm object so agents can use it.
