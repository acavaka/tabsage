"""Web scraper for downloading content from web pages"""

import logging
import re
import ssl
from typing import Dict, Any, Optional
from urllib.parse import urlparse

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    from bs4 import BeautifulSoup
    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False
    logging.warning("requests and beautifulsoup4 not installed. Install: pip install requests beautifulsoup4")

logger = logging.getLogger(__name__)


def extract_habr_content(html: str, url: str) -> Dict[str, Any]:
    """Extracts content from Habr article.
    
    Args:
        html: HTML page content
        url: Page URL
        
    Returns:
        Dictionary with title, text, author, date
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        title_elem = soup.find('h1', class_='tm-title')
        if not title_elem:
            title_elem = soup.find('title')
        title = title_elem.get_text(strip=True) if title_elem else "No title"
        
        article_body = soup.find('div', class_='tm-article-body') or soup.find('article')
        if not article_body:
            article_body = soup.find('div', {'id': 'post-content-body'}) or soup.find('div', class_='post__text')
        
        if article_body:
            for elem in article_body.find_all(['script', 'style', 'aside', 'nav', 'footer', 'header']):
                elem.decompose()
            
            for elem in article_body.find_all(class_=re.compile(r'ad|advertisement|реклама', re.I)):
                elem.decompose()
            
            text = article_body.get_text(separator='\n\n', strip=True)
        else:
            body = soup.find('body')
            text = body.get_text(separator='\n\n', strip=True) if body else ""
        
        author_elem = soup.find('a', class_='tm-user-info__username') or soup.find('span', class_='tm-user-info__username')
        author = author_elem.get_text(strip=True) if author_elem else "Unknown author"
        
        date_elem = soup.find('time') or soup.find('span', class_='tm-article-datetime-published')
        date = date_elem.get('datetime') or date_elem.get_text(strip=True) if date_elem else ""
        
        return {
            "title": title,
            "text": text,
            "author": author,
            "date": date,
            "url": url
        }
    except Exception as e:
        logger.error(f"Error extracting Habr content: {e}")
        return {
            "title": "Extraction error",
            "text": "",
            "author": "",
            "date": "",
            "url": url,
            "error": str(e)
        }


def scrape_url(url: str, timeout: int = 90) -> Dict[str, Any]:
    """Downloads and parses content from web page.
    
    Args:
        url: URL to download
        timeout: Request timeout in seconds (default: 30 for Cloud Run)
        
    Returns:
        Dictionary with title, text, metadata
    """
    if not HAS_DEPENDENCIES:
        return {
            "status": "error",
            "error_message": "requests and beautifulsoup4 not installed. Install: pip install requests beautifulsoup4",
            "url": url
        }
    
    try:
        # Create session with retry strategy
        session = requests.Session()
        
        # Retry strategy for SSL and connection errors
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,  # Increased backoff: 2s, 4s, 8s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
            raise_on_status=False,
            connect=3,  # Retry on connection errors
            read=3  # Retry on read errors
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        logger.info(f"Scraping URL: {url}")
        
        # Try with verify=True first, fallback to verify=False if SSL error
        try:
            response = session.get(url, headers=headers, timeout=timeout, verify=True)
            response.raise_for_status()
        except requests.exceptions.SSLError as ssl_error:
            logger.warning(f"SSL error with verify=True, retrying with verify=False: {ssl_error}")
            # Retry without SSL verification as fallback
            response = session.get(url, headers=headers, timeout=timeout, verify=False)
            response.raise_for_status()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as req_error:
            # If timeout or connection error, try one more time with increased timeout
            logger.warning(f"Request error, retrying with increased timeout: {req_error}")
            try:
                response = session.get(url, headers=headers, timeout=timeout * 1.5, verify=False, allow_redirects=True)
                response.raise_for_status()
            except Exception as final_error:
                logger.error(f"Final retry failed: {final_error}")
                raise
        except requests.exceptions.RequestException as req_error:
            logger.error(f"Request failed after retries: {req_error}")
            raise
        
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        if 'habr.com' in domain:
            result = extract_habr_content(response.text, url)
            result["status"] = "success"
            return result
        else:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for elem in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                elem.decompose()
            
            title_elem = soup.find('title') or soup.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else "No title"
            
            article = soup.find('article') or soup.find('main') or soup.find('div', class_=re.compile(r'content|article|post', re.I))
            if article:
                text = article.get_text(separator='\n\n', strip=True)
            else:
                body = soup.find('body')
                text = body.get_text(separator='\n\n', strip=True) if body else ""
            
            return {
                "status": "success",
                "title": title,
                "text": text,
                "url": url,
                "author": "",
                "date": ""
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching URL {url}: {e}")
        return {
            "status": "error",
            "error_message": f"Download error: {str(e)}",
            "url": url
        }
    except Exception as e:
        logger.error(f"Error parsing URL {url}: {e}")
        return {
            "status": "error",
            "error_message": f"Parsing error: {str(e)}",
            "url": url
        }

