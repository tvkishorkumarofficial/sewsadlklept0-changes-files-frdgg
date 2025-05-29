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
