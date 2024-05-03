from urllib.parse import urlparse

class Report():
    def __init__(self):
        self.longest_page = ''
        self.longest_page_length = 0
        self.subdomains = dict()
        self.unique_urls = set()
        self.stop_words = {
            'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', "aren't", 'as', 'at',
            'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by',
            "can't", 'cannot', 'could', "couldn't",
            'did', "didn't", 'do', 'does', "doesn't", 'doing', "don't", 'down', 'during',
            'each',
            'few', 'for', 'from', 'further',
            'had', "hadn't", 'has', "hasn't", 'have', "haven't", 'having', 'he', "he'd", "he'll", "he's", 'her', 'here', "here's", 'hers', 'herself', 'him', 'himself', 'his', 'how', "how's",
            'i', "i'd", "i'll", "i'm", "i've", 'if', 'in', 'into', 'is', "isn't", 'it', "it's", 'its', 'itself',
            "let's",
            'me', 'more', 'most', "mustn't", 'my', 'myself',
            'no', 'nor', 'not',
            'of', 'off', 'on', 'once', 'only', 'or', 'other', 'ought', 'our', 'ours', 'ourselves', 'out', 'over', 'own',
            'same', "shan't", 'she', "she'd", "she'll", "she's", 'should', "shouldn't", 'so', 'some', 'such',
            'than', 'that', "that's", 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', "there's", 'these', 'they', "they'd", "they'll", "they're", "they've", 'this', 'those', 'through', 'to', 'too',
            'under', 'until', 'up',
            'very',
            'was', "wasn't", 'we', "we'd", "we'll", "we're", "we've", 'were', "weren't", 'what', "what's", 'when', "when's", 'where', "where's", 'which', 'while', 'who', "who's", 'whom', 'why', "why's", 'with', "won't",
            'would', "wouldn't",
            'you', "you'd", "you'll", "you're", "you've", 'your', 'yours', 'yourself', 'yourselves'
        }
        self.total_tokens = []
    
    def tokenize(self, text):
        tokens = []
        word = ""
        for char in text:
            if 'a' <= char <= 'z' or 'A' <= char <= 'Z' or '0' <= char <= '9':
                word += char.lower()
            elif word:
                tokens.append(word)
                word = ''
        if word:
            tokens.append(word)
        return tokens
    
    def computeWordFrequencies(self, token_list):
        frequencies = {}
        for token in token_list:
            if token not in self.stop_words:
                if token in frequencies:
                    frequencies[token] += 1
                else:
                    frequencies[token] = 1
        return frequencies


    def add_current_link_data(self, soup, resp):
        tokens = self.tokenize(soup.get_text(separator=' ', strip=True))
        if len(tokens) > self.longest_page_length:
            self.longest_page = resp.url
            self.longest_page_length = len(tokens)
        self.total_tokens.append(tokens)
    
    def add_current_url_and_ics_subdomain(self, url):
        self.unique_urls.add(url)
        parsed = urlparse(url)
        if parsed.netloc.endswith(".ics.uci.edu") and parsed.netloc != "www.ics.uci.edu":
            if parsed.netloc in self.subdomains:
                self.subdomains[parsed.netloc] += 1
            else:
                self.subdomains[parsed.netloc] = 1

    def generate_report(self, filename='report.txt'):
        with open(filename, 'w') as file:
            file.write(f"Total unique pages: {len(self.unique_urls)}\n\n")
            file.write(f"Longest page: {self.longest_page} with {self.longest_page_length} words\n\n")
            file.write("Most common words:\n")
            words = self.computeWordFrequencies(self.total_tokens)
            sorted_words = sorted(words.items(), key=lambda x: x[1], reverse=True)
            # Write the top 50 words
            for word, count in sorted_words[:50]:
                file.write(f"{word}: {count}\n")
            file.write(f"\n")
            
            file.write("Subdomains in ics.uci.edu:\n")
            # Write all subdomains and their frequencies
            for subdomain, count in self.subdomains.items():
                file.write(f"{subdomain}: {count}\n")