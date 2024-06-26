import os
from dotenv import load_dotenv
import streamlit as st
import requests
from langchain.agents import AgentType, initialize_agent
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool

# Load environment variables
load_dotenv()

# Initialize ChatOpenAI
llm = ChatOpenAI(model_name="gpt-4o", openai_api_key=os.getenv("OPENAI_API_KEY"))

# Brave Search API function
def brave_search(query):
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": os.getenv("BRAVE_SEARCH_API_KEY")
    }
    params = {
        "q": query,
        "count": 5  # Limit to 5 results
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        results = response.json().get('web', {}).get('results', [])
        summary = "\n".join([f"Title: {r['title']}\nURL: {r['url']}\nDescription: {r['description']}\n" for r in results])
        urls = [r['url'] for r in results]
        return {"summary": summary, "urls": urls}
    else:
        return f"Error: Unable to fetch results. Status code: {response.status_code}"

# Create a Brave Search tool
brave_search_tool = Tool(
    name="Brave Search",
    func=brave_search,
    description="Useful for when you need to answer questions on topics ranging from reproductive health, menstrual cycles, and menopause to nutrition, fitness, and mental wellbeing. Returns a summary of search results and a list of URLs. Input should be a search query."
)

# Initialize ConversationBufferMemory
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

system_message = """You are an AI assistant specializing in women's health and wellness. 
When answering questions, always use the Brave Search tool to find relevant information. 
Summarize the search results and provide citations by including the URLs of your sources. 
Format your response as follows:

Summary of the answer based on search results.

Sources:
1. [Brief description of source 1](URL1)
2. [Brief description of source 2](URL2)
...

Remember to always cite your sources and provide accurate, helpful information."""


# Initialize the agent
agent = initialize_agent(
    [brave_search_tool],
    llm,
    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
    memory=memory,
    verbose=True,
    agent_kwargs={"system_message": system_message}
)

# Streamlit UI
st.title("AI Chatbot")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("What would you like to know?"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Generate response
    response = agent.run(prompt)

    # Check if "Sources:" is in the response
    if "Sources:" in response:
        # Split the response into summary and sources
        summary, sources = response.split("Sources:", 1)
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            st.markdown(summary.strip())
            st.markdown("Sources:" + sources)
    else:
        # If no sources, display the entire response as summary
        with st.chat_message("assistant"):
            st.markdown(response)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
