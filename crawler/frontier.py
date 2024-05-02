import os
import shelve
import re

from threading import Thread, RLock
from queue import Queue, Empty
from collections import Counter
from urllib.parse import urlparse

from utils import get_logger, get_urlhash, normalize
from scraper import is_valid

class Frontier(object):
    def __init__(self, config, restart):
        self.logger = get_logger("FRONTIER")
        self.config = config
        self.to_be_downloaded = list()
        self.depth_alert = 5
        self.unique_urls = set()
        self.subdomains = Counter()
        self.word_counter = Counter()
        self.longest_page = ('', 0)
        
        if not os.path.exists(self.config.save_file) and not restart:
            # Save file does not exist, but request to load save.
            self.logger.info(
                f"Did not find save file {self.config.save_file}, "
                f"starting from seed.")
        elif os.path.exists(self.config.save_file) and restart:
            # Save file does exists, but request to start from seed.
            self.logger.info(
                f"Found save file {self.config.save_file}, deleting it.")
            os.remove(self.config.save_file)
        # Load existing save file, or create one if it does not exist.
        self.save = shelve.open(self.config.save_file)
        if restart:
            for url in self.config.seed_urls:
                self.add_url(url, 0)
        else:
            # Set the frontier state with contents of save file.
            self._parse_save_file()

    def _parse_save_file(self):
        ''' This function can be overridden for alternate saving techniques. '''
        total_count = len(self.save)
        tbd_count = 0
        """for url, completed in self.save.values():
            if not completed and is_valid(url):
                self.to_be_downloaded.append(url)
                tbd_count += 1
        self.logger.info(
            f"Found {tbd_count} urls to be downloaded from {total_count} "
            f"total urls discovered.")"""
        for urlhash, entry in self.save.items():
            if len(entry) == 2:
                url, completed = entry
                depth = 0
            else:
                url, completed, depth = entry
            if not completed and is_valid(url) and depth < self.depth_alert:
                self.to_be_downloaded.append((url, depth))
                tbd_count += 1
        self.logger.info(
            f"Found {tbd_count} urls to be downloaded from {total_count} total urls discovered.")
    
    def get_tbd_url(self):
        try:
            return self.to_be_downloaded.pop()
        except IndexError:
            return None

    def add_url(self, url, depth):
        if depth > self.depth_alert:
            return
        url = normalize(url)
        urlhash = get_urlhash(url)
        if urlhash not in self.save:
            self.save[urlhash] = (url, False, depth)
            self.save.sync()
            self.to_be_downloaded.append((url, depth +1))
    
    def mark_url_complete(self, url):
        urlhash = get_urlhash(url)
        entry = self.save.get(urlhash)
        if entry:
            if len(entry) == 2:
                url, completed = entry
                depth = 0 
            elif len(entry) == 3:
                url, completed, depth = entry
            self.save[urlhash] = (url, True, depth)
            self.save.sync()
        else:
            self.logger.error(
                f"Completed url {url}, but have not seen it before.")
        """if urlhash not in self.save:
            # This should not happen.
            self.logger.error(
                f"Completed url {url}, but have not seen it before.")

        self.save[urlhash] = (url, True)
        self.save.sync()"""
    
    def add_page(self, url, content):
        url = normalize(url).split('#')[0]
        if url not in self.unique_urls:
            self.unique_urls.add(url)
            subdomain = urlparse(url).netloc
            self.subdomains[subdomain] += 1

            words = self.process_content(content)
            self.word_counter.update(words)
            if len(words) > self.longest_page[1]:
                self.longest_page = (url, len(words))
    
    def process_content(self, content):
        stop_words = {
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

        text = re.sub('<[^<]+?>', '', content)
        words = re.findall(r'\w+', text.lower())
        filtered_words = [word for word in words if word not in stop_words]  # Filter out stopwords
        return filtered_words

    def generate_report(self, filename='report.txt'):
        with open(filename, 'w') as file:
            file.write(f"Total unique pages: {len(self.unique_urls)}\n")
            file.write(f"Longest page: {self.longest_page[0]} with {self.longest_page[1]} words\n")
            file.write("Most common words:\n")
            for word, count in self.word_counter.most_common(50):
                file.write(f"{word}: {count}\n")
            file.write("Subdomains in ics.uci.edu:\n")
            for subdomain, count in self.subdomains.items():
                file.write(f"{subdomain}: {count}\n")