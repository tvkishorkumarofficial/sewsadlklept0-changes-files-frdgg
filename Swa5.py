def bingSearches(self, searchRelatedTerms: bool = False, relatedTermsCount: int = 0) -> None:
    """Version 2.4 - Maintains all original functionality while ensuring all searches count correctly"""
    logging.info(f"[BING] Starting {self.browser.browserType.capitalize()} Edge Bing searches...")
    self.browser.utils.goToSearch()

    remainingSearches = self.browser.getRemainingSearches()
    searchCount = 0
    
    while searchCount < remainingSearches:
        logging.info(f"[BING] {searchCount + 1}/{remainingSearches}")

        # EXACT ORIGINAL BUFFER MANAGEMENT (UNCHANGED)
        needed_searches = remainingSearches - searchCount
        if (len(self.googleTrendsShelf) <= 1 or
            len([k for k in self.googleTrendsShelf.keys() if k != LOAD_DATE_KEY]) < needed_searches):
            logging.debug("Refreshing trends cache...")
            trends = self.getGoogleTrends(needed_searches + 5)
            shuffle(trends)
            for trend in trends:
                if trend.lower() not in self.usedKeywordsShelf:
                    self.googleTrendsShelf[trend] = None
            self.googleTrendsShelf[LOAD_DATE_KEY] = date.today()

            logging.debug(
                f"BUFFER STATUS: Needed={needed_searches}, "
                f"Loaded={len(trends)}, "
                f"Now in shelf={len(self.googleTrendsShelf)-1}"
            )
            logging.debug(f"TRENDS LOADED: {list(self.googleTrendsShelf.keys())}")

        # Perform primary search and correctly track search count
        searchCount = self.bingSearch(searchRelatedTerms, relatedTermsCount, searchCount)  
        if searchCount >= remainingSearches:
            break

        sleep(randint(10, 15))  # Original random delay

    logging.info(f"[BING] Finished {self.browser.browserType.capitalize()} Edge Bing searches!")
