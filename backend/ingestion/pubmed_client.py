"""
BioMind Nexus - PubMed Client

Async client for fetching biomedical literature from NCBI PubMed.
Handles rate limiting, deduplication, and XML parsing.

Responsibilities:
- Search PubMed for Drug+Disease queries
- Fetch abstracts
- Deduplicate PMIDs
- Return structured text for extraction

Note: Agents must NOT use this. Used only by Ingestion Pipeline.
"""

import asyncio
import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Set, Optional
from backend.config import settings

class PubMedClient:
    """
    Client for NCBI E-Utils (PubMed).
    Enforces rate limits: 3 req/s with API key, 1 req/s without.
    """
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(self, email: str = "biomind@example.com", api_key: Optional[str] = None):
        self.email = email
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None
        # 1.0s delay between requests to be safe (NCBI limit is 3/s with key, 1/s without)
        self._delay = 0.35 if api_key else 1.0
        self._last_request_time = 0
        self._seen_pmids: Set[str] = set()

    def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure we have an open client, recreating if necessary."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _rate_limit(self):
        """Ensure we don't exceed rate limits."""
        import time
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._delay:
            await asyncio.sleep(self._delay - elapsed)
        self._last_request_time = time.time()

    async def search_literature(self, drug: str, disease: str, max_results: int = 50) -> List[str]:
        """
        Search PubMed for articles mentioning both drug and disease.
        Returns list of PMIDs.
        """
        await self._rate_limit()
        
        # Construct query: (drug) AND (disease) AND (has abstract)
        query = f"({drug}[Title/Abstract]) AND ({disease}[Title/Abstract])"
        
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": max_results,
            "email": self.email
        }
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            client = self._ensure_client()
            response = await client.get(f"{self.BASE_URL}/esearch.fcgi", params=params)
            response.raise_for_status()
            data = response.json()
            
            id_list = data.get("esearchresult", {}).get("idlist", [])
            return id_list
        except Exception as e:
            print(f"PubMed search failed: {e}")
            return []

    async def fetch_abstracts(self, pmids: List[str]) -> List[Dict[str, str]]:
        """
        Fetch abstracts for a list of PMIDs.
        Returns list of dicts: {pmid, title, abstract}
        """
        if not pmids:
            return []

        # Deduplicate against session history
        new_pmids = [pid for pid in pmids if pid not in self._seen_pmids]
        if not new_pmids:
            return []
            
        # Update seen set
        self._seen_pmids.update(new_pmids)

        await self._rate_limit()
        
        # E-Fetch accepts comma-separated IDs
        # Process in batches of 50 to avoid URL length issues
        results = []
        batch_size = 50
        
        for i in range(0, len(new_pmids), batch_size):
            batch = new_pmids[i:i + batch_size]
            ids_str = ",".join(batch)
            
            params = {
                "db": "pubmed",
                "id": ids_str,
                "retmode": "xml",
                "email": self.email
            }
            if self.api_key:
                params["api_key"] = self.api_key

            try:
                client = self._ensure_client()
                response = await client.get(f"{self.BASE_URL}/efetch.fcgi", params=params)
                response.raise_for_status()
                
                # Parse XML
                articles = self._parse_xml_response(response.text)
                results.extend(articles)
                
            except Exception as e:
                print(f"PubMed fetch failed for batch: {e}")
                
        return results

    def _parse_xml_response(self, xml_content: str) -> List[Dict[str, str]]:
        """Parse PubMed XML to extract Title and Abstract."""
        articles = []
        try:
            root = ET.fromstring(xml_content)
            
            for article in root.findall(".//PubmedArticle"):
                try:
                    pmid = article.find(".//PMID").text
                    
                    article_title = article.find(".//ArticleTitle")
                    title = "".join(article_title.itertext()) if article_title is not None else ""
                    
                    abstract_node = article.find(".//Abstract")
                    abstract_text = ""
                    if abstract_node is not None:
                        # Concatenate all abstract text parts (e.g. INTRODUCTION, METHODS...)
                        texts = [elem.text for elem in abstract_node.findall(".//AbstractText") if elem.text]
                        abstract_text = " ".join(texts)
                    
                    if title or abstract_text:
                        articles.append({
                            "pmid": pmid,
                            "text": f"{title}\n\n{abstract_text}",  # Combined for extraction
                            "title": title,
                            "abstract": abstract_text
                        })
                except Exception:
                    continue
                    
        except ET.ParseError:
            print("Failed to parse PubMed XML")
            
        return articles
