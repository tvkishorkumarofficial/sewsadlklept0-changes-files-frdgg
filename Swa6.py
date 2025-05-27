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
            searchCount = self.bingSearch(searchCount)  
            if searchCount >= remainingSearches:
                break

            sleep(randint(10, 15))  # Original random delay

        logging.info(f"[BING] Finished {self.browser.browserType.capitalize()} Edge Bing searches!")

    def bingSearch(self) -> None:
        availableTrends = [
            k for k in self.googleTrendsShelf.keys() 
            if k != LOAD_DATE_KEY and k.lower() not in self.usedKeywordsShelf
        ]
        if not availableTrends:
            logging.error("[BING] No unused trending keywords available globally.")
            return

        primaryKeyword = availableTrends[0]
        relatedKeywords = self.getRelatedTerms(primaryKeyword)

        logging.debug(f"PRIMARY KEYWORD: {primaryKeyword}, REMAINING TRENDS: {len(self.googleTrendsShelf)-1}")
        logging.debug(f"GLOBAL USAGE COUNT: {len(self.usedKeywordsShelf)}")

        # 1. Perform primary search first
        self.browser.utils.goToSearch()
        searchbar = self.browser.utils.waitUntilClickable(By.ID, "sb_form_q", timeToWait=60)
        searchbar.clear()
        sleep(1)
        searchbar.send_keys(primaryKeyword)
        sleep(1)
        searchbar.submit()

        # 2. Mark as used globally
        self.usedKeywordsShelf[primaryKeyword.lower()] = None
        logging.debug(f"MARKED AS USED GLOBALLY: {primaryKeyword}")

        # 3. Original local deletion
        if primaryKeyword in self.googleTrendsShelf:
            del self.googleTrendsShelf[primaryKeyword]
            logging.debug(f"POST-DELETION SHELF: {list(self.googleTrendsShelf.keys())}")

        logging.info("[COOLDOWN] Applying cooldown after primary search")
        cooldown()

        # 4. Show related terms summary
        logging.debug(
            f"RELATED TERMS SUMMARY: Found {len(relatedKeywords)} terms - "
            f"{relatedKeywords[:10]}"
        )

        # 5. Additional searchesï¿½FIXED to count every search
        searchCount = 1  # Primary search is counted

        for i in range(min(self.num_additional_searches, len(relatedKeywords))):
            relatedKeyword = relatedKeywords.pop(0)
            logging.debug(f"Searching related keyword #{i+1}: {relatedKeyword}")
            try:
                self.browser.utils.goToSearch()
                searchbar = self.browser.utils.waitUntilClickable(By.ID, "sb_form_q", timeToWait=60)
                searchbar.clear()
                sleep(1)
                searchbar.send_keys(relatedKeyword)
                sleep(1)
                searchbar.submit()
                
                logging.info(f"[COOLDOWN] Applying cooldown after related search #{i+1}")

                searchCount += 1  # FIXED: Count related searches
                logging.info(f"[BING] Search {searchCount} completed with related keyword: {relatedKeyword}")

                logging.info("[COOLDOWN] Applying cooldown after related search")
                cooldown()
            except Exception as e:
                logging.error(f"Error searching {relatedKeyword}: {e}")

        logging.info(f"[BING] Completed search cycle for trend: {primaryKeyword}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.googleTrendsShelf.close()
        self.usedKeywordsShelf.close()
