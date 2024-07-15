import os
from dotenv import load_dotenv
import streamlit as st
import requests
from langchain.agents import AgentType, initialize_agent
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.docstore.document import Document
from typing import Dict, Any
import xml.etree.ElementTree as ET
import json

# Load environment variables
load_dotenv()

# Initialize ChatOpenAI
llm = ChatOpenAI(
    model_name="gpt-4-turbo",
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    max_tokens=4096
)

# Initialize ChatOpenAI with JSON mode for structured responses
llm_json = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model_kwargs={"response_format": {"type": "json_object"}}
)

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
    description="Useful for general questions about women's health and wellness, including lifestyle, nutrition, fitness, and mental wellbeing. Returns a summary of search results and a list of URLs. Input should be a search query."
)


def get_pubmed_results(query, year_min=1900, year_max=2023, num_results=30, open_access=False):
    """Get PubMed results using E-utilities"""
    open_access_filter = "(pubmed%20pmc%20open%20access[filter])+" if open_access else ""
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&sort=relevance&datetype=pdat&mindate={year_min}&maxdate={year_max}&retmax={num_results}&term={open_access_filter}{query}"

    response = requests.get(url)
    pm_ids = response.json()['esearchresult']['idlist']
    return pm_ids

def parse_pubmed_json(doc_json, pmid):
    documents = []
    pmcid = doc_json["documents"][0]["id"]
    passages = doc_json["documents"][0]["passages"]
    lead_author = doc_json["documents"][0]["passages"][0]["infons"]["name_0"].split(";")[0][8:]  # 8: to remove "Surname:"
    year = doc_json["date"][:4]  # get year
    for passage in passages:
        if (doc_type := passage["infons"]["type"].lower()) in ["ref", "front"]:
            continue  # skip references
        elif "table" in doc_type or "caption" in doc_type or "title" in doc_type:
            continue  # skip tables, captions, titles
        if (section_type := passage["infons"]["section_type"].lower()) == "auth_cont":
            continue
        citation = f"({lead_author} {year} - {pmid})"  # create citation; eg (Smith 2021 - 12345678)
        documents.append(Document(page_content=passage["text"],
                                  metadata={
                                    "pmcid": pmcid,
                                    "pmid": pmid,
                                    "offset": passage["offset"],
                                    "section_type": section_type,
                                    "type": doc_type,
                                    "source": citation}))
    return documents

def get_fulltext_from_pmids(pmids):
    docs = []
    for pmid in pmids:
        req_url = f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/{pmid}/unicode"
        try:
            doc_json = requests.get(req_url).json()
            article_docs = parse_pubmed_json(doc_json, pmid)
            if article_docs:
                docs.extend(article_docs)
        except:
            print(f"Error with {pmid}")
    return docs

def get_abstracts_from_pmids(pmids):
    def get_nexted_xml_text(element):
        if element.text is not None:
            text = element.text.strip()
        else:
            text = ''
        for child in element:
            child_text = get_nexted_xml_text(child)
            if child_text:
                text += ' ' + child_text
        return text

    pmids_str = ','.join(pmids)
    req_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmids_str}&rettype=abstract"
    response = requests.get(req_url)
    xml_root = ET.fromstring(response.content)
    articles = xml_root.findall("PubmedArticle")
    docs = []
    for pmid_, article in zip(pmids, articles):
        if not article.find("MedlineCitation").find("Article").find("Abstract"):
            print("No abstract found")
            continue
        try:
            pmid = article.find("MedlineCitation").find("PMID").text
            year = article.find("MedlineCitation").find("DateCompleted").find("Year").text
            author = article.find("MedlineCitation").find("Article").find("AuthorList").find("Author").find("LastName").text
            citation = f"({author} {year} - {pmid})"
            abstract_node = article.find("MedlineCitation").find("Article").find("Abstract").find("AbstractText")
            abstract = get_nexted_xml_text(abstract_node)
            url = f"http://www.ncbi.nlm.nih.gov/pubmed/{pmid}"
            docs.append(Document(page_content=abstract, metadata={"source": citation, "url": url}))
        except:
            print(f"Error parsing article {pmid_}")
    print(f"Parsed {len(docs)} documents from {len(articles)} abstracts.")
    return docs

def pubmed_search(query, year_min=1990, year_max=2024, num_results=10, search_mode="abstracts"):
    pmids = get_pubmed_results(query, year_min=year_min, year_max=year_max, num_results=num_results, open_access=(search_mode == "fulltext"))
    
    if search_mode == "abstracts":
        docs = get_abstracts_from_pmids(pmids)
    elif search_mode == "fulltext":
        docs = get_fulltext_from_pmids(pmids)
    else:
        raise ValueError(f"Invalid search mode: {search_mode}")
    
    return {"results": docs, "pmids": pmids, "search_term": query}

# Create a PubMed Search tool
pubmed_search_tool = Tool(
    name="PubMed Search",
    func=pubmed_search,
    description="Useful for searching scientific and medical literature related to women's health, including reproductive health, menstrual cycles, menopause, and specific medical conditions. Returns a list of relevant papers with titles, abstracts, and URLs. Input should be a search query."
)

# Initialize ConversationBufferMemory
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

system_message = """You are an AI assistant specializing in women's health and wellness. You have access to two search tools:
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

Remember to always include at least two sources and provide accurate, helpful information."""

# Initialize the agent without specifying JSON output
agent = initialize_agent(
    [brave_search_tool, pubmed_search_tool],
    llm,  # Use the standard LLM here
    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
    memory=memory,
    verbose=True,
    agent_kwargs={"system_message": system_message}
)

# Streamlit UI
st.title("Women's Wellness AI Chatbot")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("What would you like to know about women's health and wellness?"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})


    # Call the agent with the correct input structure
    response = agent.run(input=prompt)

    # Check if "Sources:" is in the response
    if "Sources:" in response:
        # Split the response into summary and sources
        summary, sources = response.split("Sources:", 1)
        with st.chat_message("assistant"):
            st.markdown(summary.strip())
            st.markdown("Sources:" + sources)
    else:
        # If no sources, display the entire response as summary
        with st.chat_message("assistant"):
            st.markdown(response)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
