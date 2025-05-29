import dbm.dumb
import json
import logging
import shelve
from datetime import date
from enum import Enum, auto
from itertools import cycle
from random import randint, shuffle
from time import sleep
from typing import Final
import contextlib

import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import TimeoutException
from trendspy import Trends

from src.browser import Browser
from src.utils import CONFIG, getProjectRoot, cooldown, COUNTRY, makeRequestsSession

LOAD_DATE_KEY = "loadDate"
GLOBAL_KEYWORDS_DB = "used_keywords"
GLOBAL_LOAD_DATE_KEY = "globalLoadDate"  # NEW in v2.4

class RetriesStrategy(Enum):
    """Identical to original docstrings"""
    EXPONENTIAL = auto()
    CONSTANT = auto()

class Searches:
    """
    Class to handle searches in MS Rewards.
    Version 2.4 - Added global daily reset
    """
    maxRetries: Final[int] = CONFIG.get("retries").get("max")
    baseDelay: Final[float] = CONFIG.get("retries").get("base_delay_in_seconds")
    retriesStrategy = RetriesStrategy[CONFIG.get("retries").get("strategy")]

    def __init__(self, browser: Browser, searchRelatedTerms: bool = True, relatedTermsCount: int = 2, num_additional_searches=2):
        self.browser = browser
        self.webdriver = browser.webdriver
        self.searchRelatedTerms = searchRelatedTerms
        self.relatedTermsCount = relatedTermsCount
        self.num_additional_searches = num_additional_searches

        dumbDbm = dbm.dumb.open((getProjectRoot() / "google_trends").__str__())
        self.googleTrendsShelf: shelve.Shelf = shelve.Shelf(dumbDbm)
        
        globalDbm = dbm.dumb.open((getProjectRoot() / GLOBAL_KEYWORDS_DB).__str__())
        self.usedKeywordsShelf: shelve.Shelf = shelve.Shelf(globalDbm)
        
        global_load_date = self.usedKeywordsShelf.get(GLOBAL_LOAD_DATE_KEY)
        if global_load_date is None or global_load_date < date.today():
            self.usedKeywordsShelf.clear()
            self.usedKeywordsShelf[GLOBAL_LOAD_DATE_KEY] = date.today()

        loadDate: date | None = None
        if LOAD_DATE_KEY in self.googleTrendsShelf:
            loadDate = self.googleTrendsShelf[LOAD_DATE_KEY]

        if loadDate is None or loadDate < date.today():
            self.googleTrendsShelf.clear()
            self.googleTrendsShelf[LOAD_DATE_KEY] = date.today()
            trends = self.getGoogleTrends(
                self.browser.getRemainingSearches(desktopAndMobile=True).getTotal()
            )
            shuffle(trends)
            for trend in trends:
                if trend.lower() not in self.usedKeywordsShelf:
                    self.googleTrendsShelf[trend] = None
            logging.debug(f"TRENDS LOADED: {list(self.googleTrendsShelf.keys())}")

        # Automatically trigger searches when an instance is created
        logging.info("Automatically starting Bing searches inside Searches class")
        self.bingSearches(searchRelatedTerms=self.searchRelatedTerms, relatedTermsCount=self.relatedTermsCount)
        logging.info("Search execution completed!")

    def getGoogleTrends(self, wordsCount: int) -> list[str]:
        """Fetch trends using trendspy"""
        logging.debug("Fetching trends via trendspy...")
        try:
            trends = Trends().trending_now(geo=self.browser.localeGeo)[:wordsCount]
            return [t.keyword.lower() for t in trends]
        except Exception as e:
            logging.error(f"Error fetching trends: {e}")
            return []

    def extract_json_from_response(self, text: str):
        """Maintained for backward compatibility"""
        logging.debug("Extracting JSON from API response")
        for line in text.splitlines():
            trimmed = line.strip()
            if trimmed.startswith('[') and trimmed.endswith(']'):
                try:
                    intermediate = json.loads(trimmed)
                    data = json.loads(intermediate[0][2])
                    logging.debug("JSON extraction successful")
                    return data[1]
                except Exception as e:
                    logging.warning(f"Error parsing JSON: {e}")
                    continue
        logging.error("No valid JSON found in response")
        return None

    def getRelatedTerms(self, term: str) -> list[str]:
        """Fetch related terms from Bing's autocomplete API"""
        relatedTerms = (
            makeRequestsSession()
            .get(
                f"https://api.bing.com/osjson.aspx?query={term}",
                headers={"User-agent": self.browser.userAgent},
            )
            .json()[1]
        )
        uniqueTerms = list(dict.fromkeys(relatedTerms))
        uniqueTerms = [t for t in uniqueTerms if t.lower() != term.lower()]
        return uniqueTerms

    def bingSearches(self, searchRelatedTerms: bool = False, relatedTermsCount: int = 0) -> None:
        logging.info(f"[BING] Starting {self.browser.browserType.capitalize()} Edge Bing searches...")
        self.browser.utils.goToSearch()

        remainingSearches = self.browser.getRemainingSearches()
        searchCount = 0
        while searchCount < remainingSearches:
            logging.info(f"[BING] {searchCount + 1}/{remainingSearches}")
            searchCount = self.bingSearch(searchRelatedTerms, relatedTermsCount, searchCount)
            if searchCount >= remainingSearches:
                break

            if searchRelatedTerms:
                rootTerm = list(self.googleTrendsShelf.keys())[1]
                terms = self.getRelatedTerms(rootTerm)
                uniqueTerms = list(dict.fromkeys(terms))
                uniqueTerms = [t for t in uniqueTerms if t.lower() != rootTerm.lower()]
                for i, _ in enumerate(uniqueTerms[:relatedTermsCount]):
                    searchCount = self.bingSearch(searchRelatedTerms, relatedTermsCount, searchCount)
                    if searchCount >= remainingSearches:
                        break

        logging.info(f"[BING] Finished {self.browser.browserType.capitalize()} Edge Bing searches!")

    def bingSearch(self, searchRelatedTerms: bool = False, relatedTermsCount: int = 0, searchCount: int = 0) -> int:
        pointsBefore = self.browser.utils.getAccountPoints()
        rootTerm = list(self.googleTrendsShelf.keys())[1]
        terms = self.getRelatedTerms(rootTerm)
        uniqueTerms = list(dict.fromkeys(terms))
        uniqueTerms = [t for t in uniqueTerms if t.lower() != rootTerm.lower()]
        logging.debug(f"rootTerm={rootTerm}")
        logging.debug(f"uniqueTerms={uniqueTerms}")

        if searchRelatedTerms:
            terms = [rootTerm] + uniqueTerms[:relatedTermsCount]
        else:
            terms = [rootTerm]

        searchbar = self.browser.utils.waitUntilClickable(By.ID, "sb_form_q", timeToWait=40)
        searchbar.clear()
        term = terms[0]
        searchbar.send_keys(term)
        searchbar.submit()

        searchCount += 1
        logging.info(f"[BING] {searchCount} searches completed")

        del self.googleTrendsShelf[rootTerm]
        logging.debug(f"Deleted '{rootTerm}'. Remaining terms: {list(self.googleTrendsShelf.keys())}")

        sleep(randint(220, 280))
        return searchCount

def bingSearches(self, searchRelatedTerms: bool = False, relatedTermsCount: int = 2) -> None:
    logging.info(f"[BING] Starting {self.browser.browserType.capitalize()} Edge Bing searches...")
    self.browser.utils.goToSearch()

    remainingSearches = self.browser.getRemainingSearches()
    searchCount = 0
    while searchCount < remainingSearches:
        logging.info(f"[BING] {searchCount + 1}/{remainingSearches}")
        searchCount = self.bingSearch(searchRelatedTerms, relatedTermsCount, searchCount)
        if searchCount >= remainingSearches:
            break

        if searchRelatedTerms:
            rootTerm = list(self.googleTrendsShelf.keys())[1]
            terms = self.getRelatedTerms(rootTerm)
            uniqueTerms = list(dict.fromkeys(terms))
            uniqueTerms = [t for t in uniqueTerms if t.lower() != rootTerm.lower()]
            
            # Limit related searches to the specified count
            for i, related_term in enumerate(uniqueTerms[:relatedTermsCount]):
                searchCount = self.bingSearch(searchRelatedTerms, relatedTermsCount, searchCount)
                if searchCount >= remainingSearches:
                    break

    logging.info(f"[BING] Finished {self.browser.browserType.capitalize()} Edge Bing searches!")

def bingSearch(self, searchRelatedTerms: bool = False, relatedTermsCount: int = 0, searchCount: int = 0) -> int:
    pointsBefore = self.browser.utils.getAccountPoints()
    rootTerm = list(self.googleTrendsShelf.keys())[1]
    terms = self.getRelatedTerms(rootTerm)
    uniqueTerms = list(dict.fromkeys(terms))
    uniqueTerms = [t for t in uniqueTerms if t.lower() != rootTerm.lower()]
    logging.debug(f"rootTerm={rootTerm}")
    logging.debug(f"uniqueTerms={uniqueTerms}")

    if searchRelatedTerms:
        terms = [rootTerm] + uniqueTerms[:relatedTermsCount]
    else:
        terms = [rootTerm]

    logging.debug(f"terms={terms}")

    searchbar = self.browser.utils.waitUntilClickable(By.ID, "sb_form_q", timeToWait=40)
    searchbar: WebElement
    termsCycle = cycle(terms)
    for _ in range(3):
        searchbar.clear()
        term = next(termsCycle)
        logging.debug(f"term={term}")
        searchbar.send_keys(term)
        with contextlib.suppress(TimeoutException):
            WebDriverWait(self.webdriver, 40).until(
                expected_conditions.text_to_be_present_in_element_value((By.ID, "sb_form_q"), term)
            )
            break
        logging.debug("error send_keys")
    else:
        raise TimeoutException

    searchbar.submit()
    pointsAfter = self.browser.utils.getAccountPoints()

    searchCount += 1
    logging.info(f"[BING] {searchCount} searches completed")

    # ALWAYS DELETE THE TERM (SUCCESS OR FAILURE)
    del self.googleTrendsShelf[rootTerm]
    logging.debug(f"Deleted '{rootTerm}'. Remaining terms: {list(self.googleTrendsShelf.keys())}")

    sleep(randint(220, 280))

    if searchRelatedTerms:
        logging.debug("Starting additional searches for related terms")
        for i, related_term in enumerate(uniqueTerms):
            if i >= relatedTermsCount:
                break
            try:
                searchbar = self.browser.utils.waitUntilClickable(By.ID, "sb_form_q", timeToWait=40)
                searchbar.clear()
                logging.debug(f"related term={related_term}")
                searchbar.send_keys(related_term)
                searchbar.submit()
                searchCount += 1
                logging.info(f"[BING] {searchCount} searches completed (including additional terms)")
                sleep(randint(200, 300))
            except TimeoutException:
                logging.warning(f"Timeout while searching for related term: {related_term}")

    return searchCount
