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
            if not self.save:
                for url in self.config.seed_urls:
                    self.add_url(url)

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
        for urlhash, (url, completed, depth) in self.save.items():
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
            self.save[urlhash] = (url, False)
            self.save.sync()
            self.to_be_downloaded.append(url)
    
    def mark_url_complete(self, url):
        urlhash = get_urlhash(url)
        if urlhash in self.save:
            _, _, depth = self.save[urlhash]
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
        text = re.sub('<[^<]+?>', '', content)
        words = re.findall(r'\w+', text.lower())
        return words

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