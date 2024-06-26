import os
import shelve

from threading import Thread, RLock
from queue import Queue, Empty
from urllib.parse import urlparse

from utils import get_logger, get_urlhash, normalize
from scraper import is_valid

class Frontier(object):
    def __init__(self, config, restart):
        self.logger = get_logger("FRONTIER")
        self.config = config
        self.to_be_downloaded = list()
        self.depth_alert = 5
        
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
 