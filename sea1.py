def bingSearches(self) -> None:
    """Version 2.4 - Full search counting including related searches"""
    logging.info(f"[BING] Starting {self.browser.browserType.capitalize()} Edge Bing searches...")
    self.browser.utils.goToSearch()

    remaining = self.browser.getRemainingSearches(desktopAndMobile=True)
    total_needed = remaining.desktop if self.browser.browserType == "desktop" else remaining.mobile
    searchCount = 0

    while searchCount < total_needed:
        logging.info(f"[BING] {searchCount + 1}/{total_needed}")
        
        # Original buffer management
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

        # Get available trends
        availableTrends = [
            k for k in self.googleTrendsShelf.keys() 
            if k != LOAD_DATE_KEY and k.lower() not in self.usedKeywordsShelf
        ]
        if not availableTrends:
            logging.error("[BING] No unused trending keywords available globally.")
            break

        # Perform primary search (counts as 1)
        primaryKeyword = availableTrends[0]
        self._performSearch(primaryKeyword)
        self.usedKeywordsShelf[primaryKeyword.lower()] = None
        if primaryKeyword in self.googleTrendsShelf:
            del self.googleTrendsShelf[primaryKeyword]
        searchCount += 1
        if searchCount >= total_needed:
            break

        # Perform related searches (each counts as 1)
        relatedKeywords = self.getRelatedTerms(primaryKeyword)
        for relatedKeyword in relatedKeywords[:self.num_additional_searches]:
            if searchCount >= total_needed:
                break
            # Perform search with original cooldown
            self.bingSearch()
            searchCount += 1
            sleep(randint(10, 15))  # Original random delay

        # Update remaining count
        remaining = self.browser.getRemainingSearches(desktopAndMobile=True)
        total_needed = remaining.desktop if self.browser.browserType == "desktop" else remaining.mobile

    logging.info(f"[BING] Finished {self.browser.browserType.capitalize()} Edge Bing searches!")
