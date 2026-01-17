"""
Service layer for PubMed/NCBI E-utilities API interactions.
Retrieves biomedical literature for drug repurposing research.

Design: Agents call this service; API logic stays in service layer.
"""

import httpx
from typing import List, Dict, Any, Optional
from xml.etree import ElementTree
import asyncio

from backend.config import settings


# NCBI E-utilities base URLs
EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ESEARCH_URL = f"{EUTILS_BASE}/esearch.fcgi"
EFETCH_URL = f"{EUTILS_BASE}/efetch.fcgi"


async def search_pubmed(
    query: str,
    max_results: int = None,
    sort: str = "relevance"
) -> List[str]:
    """
    Search PubMed and return list of PMIDs.
    """
    max_results = max_results or settings.PUBMED_MAX_RESULTS
    
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "sort": sort,
        "retmode": "json",
        "email": settings.PUBMED_EMAIL,
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(ESEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("esearchresult", {}).get("idlist", [])
        except Exception as e:
            print(f"PubMed search error: {e}")
            return []


async def fetch_pubmed_articles(pmids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch article details for given PMIDs.
    
    Args:
        pmids: List of PubMed IDs
    
    Returns:
        List of article metadata dicts
    """
    if not pmids:
        return []
    
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "email": settings.PUBMED_EMAIL,
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(EFETCH_URL, params=params)
            response.raise_for_status()
            return _parse_pubmed_xml(response.text)
        except Exception as e:
            print(f"PubMed fetch error: {e}")
            return []


def _parse_pubmed_xml(xml_text: str) -> List[Dict[str, Any]]:
    """Parse PubMed XML response into structured data."""
    articles = []
    
    try:
        root = ElementTree.fromstring(xml_text)
        
        for article_elem in root.findall(".//PubmedArticle"):
            article = _parse_article(article_elem)
            if article:
                articles.append(article)
    except Exception as e:
        print(f"XML parsing error: {e}")
    
    return articles


def _parse_article(article_elem) -> Optional[Dict[str, Any]]:
    """Parse a single PubmedArticle element."""
    try:
        medline = article_elem.find(".//MedlineCitation")
        if medline is None:
            return None
        
        pmid_elem = medline.find(".//PMID")
        pmid = pmid_elem.text if pmid_elem is not None else ""
        
        article = medline.find(".//Article")
        if article is None:
            return None
        
        # Title
        title_elem = article.find(".//ArticleTitle")
        title = title_elem.text if title_elem is not None else "No title"
        
        # Abstract
        abstract_elem = article.find(".//Abstract/AbstractText")
        abstract = abstract_elem.text if abstract_elem is not None else ""
        
        # Authors
        authors = []
        for author_elem in article.findall(".//Author"):
            last_name = author_elem.find("LastName")
            fore_name = author_elem.find("ForeName")
            if last_name is not None:
                name = last_name.text
                if fore_name is not None:
                    name = f"{fore_name.text} {name}"
                authors.append(name)
        
        # Year
        year = None
        pub_date = article.find(".//PubDate/Year")
        if pub_date is not None:
            try:
                year = int(pub_date.text)
            except:
                pass
        
        # Journal
        journal_elem = article.find(".//Journal/Title")
        journal = journal_elem.text if journal_elem is not None else ""
        
        # DOI
        doi = None
        for id_elem in article_elem.findall(".//ArticleId"):
            if id_elem.get("IdType") == "doi":
                doi = id_elem.text
                break
        
        return {
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "authors": authors[:5],  # Limit to first 5 authors
            "year": year,
            "journal": journal,
            "doi": doi,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        }
    except Exception as e:
        print(f"Article parsing error: {e}")
        return None


async def search_drug_disease_literature(
    drug: str,
    disease: str,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for literature about drug-disease relationships.
    
    Args:
        drug: Drug name
        disease: Disease name
        max_results: Maximum articles to return
    
    Returns:
        List of article dicts with relevance info
    """
    # Construct search query for drug repurposing
    query = f"({drug}[Title/Abstract]) AND ({disease}[Title/Abstract]) AND (repurposing OR therapeutic OR treatment OR mechanism)"
    
    pmids = await search_pubmed(query, max_results=max_results)
    
    if not pmids:
        # Try broader search
        query = f"({drug}[Title/Abstract]) AND ({disease}[Title/Abstract])"
        pmids = await search_pubmed(query, max_results=max_results)
    
    articles = await fetch_pubmed_articles(pmids)
    
    # Add relevance scoring based on keyword presence
    for article in articles:
        score = _calculate_relevance(article, drug, disease)
        article["relevance_score"] = score
    
    # Sort by relevance
    articles.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return articles


def _calculate_relevance(article: Dict, drug: str, disease: str) -> float:
    """Calculate relevance score for an article."""
    score = 0.5  # Base score
    
    text = f"{article.get('title', '')} {article.get('abstract', '')}".lower()
    drug_lower = drug.lower()
    disease_lower = disease.lower()
    
    # Check title mentions
    title = article.get("title", "").lower()
    if drug_lower in title:
        score += 0.15
    if disease_lower in title:
        score += 0.15
    
    # Check abstract mentions
    abstract = article.get("abstract", "").lower()
    if drug_lower in abstract:
        score += 0.1
    if disease_lower in abstract:
        score += 0.1
    
    # Boost for repurposing keywords
    repurposing_keywords = ["repurpos", "reposit", "mechanism", "therapeutic", "treatment", "efficacy"]
    for keyword in repurposing_keywords:
        if keyword in text:
            score += 0.02
    
    return min(1.0, score)


async def search_entity_literature(
    entity_name: str,
    entity_type: str = "any",
    max_results: int = 5
) -> List[Dict[str, Any]]:
    """
    Search for literature about a specific entity.
    """
    # Customize query based on entity type
    if entity_type == "drug":
        query = f"{entity_name}[Title/Abstract] AND (pharmacology OR mechanism OR therapeutic)"
    elif entity_type == "disease":
        query = f"{entity_name}[Title/Abstract] AND (treatment OR therapy OR pathogenesis)"
    elif entity_type == "gene":
        query = f"{entity_name}[Title/Abstract] AND (signaling OR pathway OR mutation)"
    else:
        query = f"{entity_name}[Title/Abstract]"
    
    pmids = await search_pubmed(query, max_results=max_results)
    return await fetch_pubmed_articles(pmids)
