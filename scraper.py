import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from simhash_detection import page_content, detect_near_duplicates

import report

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_content(soup):
    """Extract plain text content from HTML, 
    removing all scripts and styles."""
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    return text

robots_cache = {}
def can_fetch_robot(url):
    parsed_url = urlparse(url)
    root_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    if root_url not in robots_cache:
        rp = RobotFileParser()
        rp.set_url(f"{root_url}/robots.txt")
        rp.read()
        robots_cache[root_url] = rp
    return robots_cache[root_url].can_fetch("*", url)

def extract_next_links(url, resp):
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    if resp.status != 200 or not resp.raw_response:
        return []  # Ignore non-200 responses and empty content
    content = extract_content(resp.raw_response.content)
    page_simhash = page_content(url, content)
    if detect_near_duplicates(url, page_simhash):
        return []
    soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
    report.add_current_link_data(soup, resp)
    found_links = set()
    for link in soup.find_all('a', href=True):
        abs_url = urljoin(resp.url, link['href'])
        if is_valid(abs_url) and can_fetch_robot(abs_url):
            found_links.add(abs_url)
            report.add_current_url_to_set(abs_url)


    return list(found_links)

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        valid_domains = [
            ".ics.uci.edu",
            ".cs.uci.edu",
            ".informatics.uci.edu",
            ".stat.uci.edu"
        ]
        domain = parsed.netloc
        if not any(domain.endswith(d) for d in valid_domains):
            return False
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise
