import requests
import xml.etree.ElementTree as ET
from langchain.docstore.document import Document
from typing import Dict, Any
from config import BRAVE_SEARCH_API_KEY

def brave_search(query):
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_SEARCH_API_KEY
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

