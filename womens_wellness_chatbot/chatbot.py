from langchain.agents import AgentType, initialize_agent
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool
from config import OPENAI_API_KEY
from search_tools import brave_search, pubmed_search

class Chatbot:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name="gpt-4-0125-preview",
            openai_api_key=OPENAI_API_KEY,
            max_tokens=4096
        )
        
        self.brave_search_tool = Tool(
            name="Brave Search",
            func=brave_search,
            description="Useful for general questions about women's health and wellness, including lifestyle, nutrition, fitness, and mental wellbeing. Returns a summary of search results and a list of URLs. Input should be a search query."
        )
        
        self.pubmed_search_tool = Tool(
            name="PubMed Search",
            func=pubmed_search,
            description="Useful for searching scientific and medical literature related to women's health, including reproductive health, menstrual cycles, menopause, and specific medical conditions. Returns a list of relevant papers with titles, abstracts, and URLs. Input should be a search query."
        )
        
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        
        self.system_message = """You are an AI assistant specializing in women's health and wellness. Provide detailed, comprehensive responses to queries, covering multiple aspects of the topic when relevant. You have access to two search tools:
        1. Brave Search: Use this for general questions about women's health, lifestyle, nutrition, fitness, and mental wellbeing.
        2. PubMed Search: Use this for more specific medical questions or when you need scientific literature on women's health topics.

        Generate the response in the following format:

        "Summary of the answer based on search results.
        Sources:
        1. URL1
        2. URL2"

        Choose the appropriate tool(s) based on the nature of the question:
        - For general wellness queries, use Brave Search.
        - For specific medical or scientific questions, use PubMed Search.
        - For complex queries that may benefit from both general and scientific information, use both tools.
        - If one search doesn't yield any results, use the other one

        Remember to always include at least two sources and provide accurate, helpful information."""
        
        self.agent = initialize_agent(
            [self.brave_search_tool, self.pubmed_search_tool],
            self.llm,
            agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
            memory=self.memory,
            verbose=True,
            agent_kwargs={"system_message": self.system_message}
        )
    
    def get_response(self, prompt):
        return self.agent.run(input=prompt)
