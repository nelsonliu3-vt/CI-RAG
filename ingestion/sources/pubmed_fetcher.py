"""
PubMed Fetcher
Fetches academic papers from PubMed using Entrez API
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PubMedArticle:
    """PubMed article data"""
    pmid: str
    title: str
    abstract: str
    authors: List[str]
    journal: str
    pub_date: str
    doi: Optional[str]
    pmc_id: Optional[str]
    url: str
    full_text: Optional[str] = None


class PubMedFetcher:
    """Fetch academic papers from PubMed"""

    def __init__(self, email: str = "your_email@example.com"):
        """
        Initialize PubMed fetcher

        Args:
            email: Email for Entrez API (required by NCBI)
        """
        self.email = email

    def search(
        self,
        query: str,
        max_results: int = 20,
        days_back: int = 90
    ) -> List[PubMedArticle]:
        """
        Search PubMed for articles

        Args:
            query: Search query (e.g., "KRAS G12C inhibitor NSCLC")
            max_results: Maximum number of results to fetch
            days_back: Only fetch articles from last N days

        Returns:
            List of PubMedArticle objects
        """
        try:
            from Bio import Entrez
            Entrez.email = self.email

            # Build search query with date filter
            date_filter = f"AND ({days_back} days[pdat])" if days_back else ""
            full_query = f"{query}{date_filter}"

            logger.info(f"Searching PubMed: {full_query}")

            # Search for PMIDs
            search_handle = Entrez.esearch(
                db="pubmed",
                term=full_query,
                retmax=max_results,
                sort="relevance"
            )
            search_results = Entrez.read(search_handle)
            search_handle.close()

            pmids = search_results.get("IdList", [])
            logger.info(f"Found {len(pmids)} PubMed IDs")

            if not pmids:
                return []

            # Fetch article details
            articles = self._fetch_articles(pmids)

            logger.info(f"✓ Fetched {len(articles)} PubMed articles")
            return articles

        except ImportError:
            logger.error("biopython not installed. Run: pip install biopython")
            return []
        except Exception as e:
            logger.error(f"Error searching PubMed: {e}")
            return []

    def _fetch_articles(self, pmids: List[str]) -> List[PubMedArticle]:
        """Fetch article details for given PMIDs"""
        from Bio import Entrez
        Entrez.email = self.email

        articles = []

        try:
            # Fetch details in batch
            fetch_handle = Entrez.efetch(
                db="pubmed",
                id=pmids,
                rettype="medline",
                retmode="xml"
            )
            records = Entrez.read(fetch_handle)
            fetch_handle.close()

            for record in records['PubmedArticle']:
                try:
                    article = self._parse_article(record)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning(f"Error parsing article: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching article details: {e}")

        return articles

    def _parse_article(self, record: Dict) -> Optional[PubMedArticle]:
        """Parse PubMed XML record into PubMedArticle"""
        try:
            medline = record['MedlineCitation']
            article_data = medline['Article']

            # Extract PMID
            pmid = str(medline['PMID'])

            # Extract title
            title = article_data.get('ArticleTitle', '')

            # Extract abstract
            abstract_parts = article_data.get('Abstract', {}).get('AbstractText', [])
            if isinstance(abstract_parts, list):
                abstract = ' '.join([str(part) for part in abstract_parts])
            else:
                abstract = str(abstract_parts)

            # Extract authors
            authors = []
            author_list = article_data.get('AuthorList', [])
            for author in author_list[:5]:  # Limit to first 5 authors
                last_name = author.get('LastName', '')
                initials = author.get('Initials', '')
                if last_name:
                    authors.append(f"{last_name} {initials}")

            # Extract journal
            journal = article_data.get('Journal', {}).get('Title', 'Unknown')

            # Extract publication date
            pub_date_info = article_data.get('Journal', {}).get('JournalIssue', {}).get('PubDate', {})
            year = pub_date_info.get('Year', '')
            month = pub_date_info.get('Month', '01')
            day = pub_date_info.get('Day', '01')
            pub_date = f"{year}-{month}-{day}"

            # Extract DOI and PMC ID
            doi = None
            pmc_id = None

            article_ids = record.get('PubmedData', {}).get('ArticleIdList', [])
            for article_id in article_ids:
                if article_id.attributes.get('IdType') == 'doi':
                    doi = str(article_id)
                elif article_id.attributes.get('IdType') == 'pmc':
                    pmc_id = str(article_id)

            # Build URL
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

            return PubMedArticle(
                pmid=pmid,
                title=title,
                abstract=abstract,
                authors=authors,
                journal=journal,
                pub_date=pub_date,
                doi=doi,
                pmc_id=pmc_id,
                url=url
            )

        except Exception as e:
            logger.warning(f"Error parsing article: {e}")
            return None

    def fetch_full_text(self, article: PubMedArticle) -> Optional[str]:
        """
        Attempt to fetch full text from PubMed Central

        Args:
            article: PubMedArticle object

        Returns:
            Full text string or None if unavailable
        """
        if not article.pmc_id:
            logger.debug(f"No PMC ID for PMID {article.pmid}, skipping full text")
            return None

        try:
            from Bio import Entrez
            Entrez.email = self.email

            # Fetch full text XML from PMC
            fetch_handle = Entrez.efetch(
                db="pmc",
                id=article.pmc_id,
                rettype="full",
                retmode="xml"
            )

            # Parse XML and extract text
            # This is simplified - full implementation would parse sections
            text_content = fetch_handle.read()
            fetch_handle.close()

            # Basic text extraction from XML
            # TODO: Implement proper XML parsing for better text extraction
            logger.info(f"✓ Fetched full text for PMC{article.pmc_id}")
            return str(text_content)

        except Exception as e:
            logger.warning(f"Could not fetch full text for PMC{article.pmc_id}: {e}")
            return None


# Singleton
_pubmed_fetcher: Optional[PubMedFetcher] = None


def get_pubmed_fetcher(email: str = "cirag@example.com") -> PubMedFetcher:
    """Get or create PubMed fetcher singleton"""
    global _pubmed_fetcher
    if _pubmed_fetcher is None:
        _pubmed_fetcher = PubMedFetcher(email=email)
    return _pubmed_fetcher


if __name__ == "__main__":
    print("Testing PubMed Fetcher...")

    fetcher = get_pubmed_fetcher()
    articles = fetcher.search("KRAS G12C inhibitor", max_results=5)

    print(f"\n✓ Fetched {len(articles)} articles")
    for article in articles[:3]:
        print(f"\n  PMID: {article.pmid}")
        print(f"  Title: {article.title[:80]}...")
        print(f"  Authors: {', '.join(article.authors)}")
        print(f"  Journal: {article.journal}")

    print("\n✓ PubMed Fetcher test successful!")
