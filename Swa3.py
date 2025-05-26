def bingSearches(self) -> None:
    """Original code structure with all searches counting."""
    logging.info(f"[BING] Starting {self.browser.browserType.capitalize()} Edge Bing searches...")
    self.browser.utils.goToSearch()

    remaining = self.browser.getRemainingSearches(desktopAndMobile=True)
    total_needed = remaining.desktop if self.browser.browserType == "desktop" else remaining.mobile
    searchCount = 0

    while searchCount < total_needed:
        # Calculate remaining searches (1 primary + N related)
        remaining_searches = total_needed - searchCount
        searches_per_cycle = 1 + min(self.num_additional_searches, remaining_searches - 1)
      
        logging.info(f"[BING] {searchCount + 1}/{total_needed}")

        # EXACT ORIGINAL BUFFER MANAGEMENT (UNCHANGED)
        needed_searches = total_needed - searchCount
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

        # Perform searches and count ALL (primary + related)
        searchCount += self.bingSearch(max_searches=searches_per_cycle)
        sleep(randint(10, 15))  # Original random delay

    logging.info(f"[BING] Finished {self.browser.browserType.capitalize()} Edge Bing searches!")
