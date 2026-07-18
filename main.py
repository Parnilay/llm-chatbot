import os
import requests
from typing import Optional
from langchain.agents import create_agent
from pydantic import BaseModel, Field
import time
import asyncio
from dotenv import load_dotenv
from tavily import TavilyClient
from langchain_exa import ExaSearchResults
from langchain_core.tools import tool
load_dotenv()

class GitHubRepo(BaseModel):
    ''' A GitHub Repo with details'''
    title: Optional[str] = Field(description="The title of the repository", default=None)
    url: Optional[str] = Field(description="The URL of the repository", default=None)
    published_date: Optional[str] = Field(description="The date when the repository was published", default=None)
    author: Optional[str] = Field(description="The author of the repository", default=None)

@tool(args_schema=GitHubRepo)
def submit_final_repo(title: Optional[str] = None, url: Optional[str] = None, published_date: Optional[str] = None, author: Optional[str] = None):
    """Call this tool ONLY when you have found the final topmost Github repository to present to the user."""
    # We just return the structured data. LangGraph will capture this as a tool message.
    return {"title": title, "url": url, "published_date": published_date, "author": author}

async def get_news(topic: str) -> str:
    '''
    Use this tool to get the latest news about a topic, some person, any event, etc. You can get the latest information about anything. The output will always be a string.

    Args:
        topic (str): The topic you want to get the latest news about.
    
    Returns:
        str: The latest news about the topic.
    '''
    tavily_client = TavilyClient()
    search_results = tavily_client.search(query=topic, count=10)
    return search_results

async def get_repo_data(query: str) -> dict:
    '''
    Use this tool to get the latest information about any github repository.
    The output is a dictionary containing the information about the repository.
    
    Args:
        query (str): The query you want to get the latest information about.
    
    Returns:
        dict: The latest information about the repository.
    '''
    headers = {
        "x-api-key": os.getenv("EXA_API_KEY"),
        "content-type": "application/json"
    }
    payload = {
        "query": query,
        "numResults": 2,
        "includeDomains": ["github.com"]
    }
    
    response = await asyncio.to_thread(
        requests.post, "https://api.exa.ai/search", headers=headers, json=payload
    )
    return response.json()

async def build_chatbot():
    llm_agent = create_agent(
        model = "groq:llama-3.3-70b-versatile",
        system_prompt = (
            "You are a highly capable AI assistant with access to search tools.\n\n"
            "SCENARIO A - GITHUB REPOSITORIES:\n"
            "If the user asks about a GitHub repository, you must:\n"
            "1. FIRST, use 'get_repo_data' to search for the repository details.\n"
            "2. CRITICAL: You must wait for the search results to be returned! Do NOT call any other tools yet.\n"
            "3. ONLY AFTER reading the results, use the 'submit_final_repo' tool to submit the final structured data.\n\n"
            "SCENARIO B - NEWS AND GENERAL SEARCH:\n"
            "If the user asks about news, people, or events:\n"
            "1. Use the 'get_news' tool to search for the information.\n"
            "2. Provide your final answer as normal conversational text."
        ),
        tools=[get_news, get_repo_data, submit_final_repo]
    )
    return llm_agent

async def main():
    # print("Hello from llm-chatbot!")
    # llm_agent = await build_chatbot()
    # print(llm_agent)
    # response = await llm_agent.ainvoke({"messages": [{"role": "user", "content": "Can you tell me about the financial performance of Apple in 2025?"}]})
    # print("------")
    # print(response["messages"][-1].content)
    # print("------")
    print("Hello from llm-chatbot!")
    llm_agent = await build_chatbot()
    print(llm_agent)
    
    response = await llm_agent.ainvoke({"messages": [{"role": "user", "content": "What are the popular github repositories for Agentic AI which were published today? Provide me the topmost one."}]})
    
    print("\n--- FULL CONVERSATION HISTORY ---")
    for msg in response["messages"]:
        # Print who sent the message (user, ai, or tool)
        print(f"\n[{msg.type.upper()}]")
        
        # If the AI called a tool, print the tool call details
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            print(f"Decided to call tool: {msg.tool_calls}")
        # Print the actual text/data of the message
        if msg.content:
            # Slicing to 200 chars just so it doesn't flood your terminal
            print(f"Content: {str(msg.content)[:200]}...")
    print("\n--- FINAL ANSWER ---")
    
    # 1. Look for the submit_final_repo tool call in the conversation history
    structured_data = None
    for msg in response["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if tool_call["name"] == "submit_final_repo":
                    # Instantiate your Pydantic model with the tool arguments
                    structured_data = GitHubRepo(**tool_call["args"])
                    break
        if structured_data:
            break
            
    # 2. Print the structured data if found, otherwise fall back to normal text
    if structured_data:
        print("🎉 SUCCESS! Extracted Pydantic Model:")
        print(f"  Pydantic Representation: {repr(structured_data)}")
        print(f"  Title: {structured_data.title}")
        print(f"  URL: {structured_data.url}")
        print(f"  Published Date: {structured_data.published_date}")
        print(f"  Author: {structured_data.author}")
    else:
        print("Conversational response:")
        print(response["messages"][-1].content)
        
    print("--------------------")

if __name__ == "__main__":
    start_time = time.perf_counter()
    asyncio.run(main())
    end_time = time.perf_counter()
    print(f"Time taken: {end_time - start_time} seconds")
    
