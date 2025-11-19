#!/usr/bin/env python3
# https://pythonspeed.com/articles/activate-virtualenv-dockerfile/
# https://gabrielgomes61320.medium.com/using-containers-to-simulate-python-isolated-environments-72960d73f413


import asyncio
import datetime
import logging
import sys

from playwright.async_api import async_playwright

logger = logging.getLogger("mcdsurvey")
logger_hdl = logging.StreamHandler()
logger_hdl.setFormatter(
    logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
)
logger.addHandler(logger_hdl)
logger.setLevel(logging.INFO)


class Scraper:
    """A class for performing bulk web scraping using Browserless.io service.

    This class provides an interface to make bulk web scraping requests using
    Playwright and leveraging Browserless.io service. Given an asyncio Queue,
    a single browser instance will scrape using multiple pages until the queue
    is empty.

    It optimizes the unit usage of the service by issuing as many requests
    using a single Chromium browser instance with a user-defined number of
    browser pages. According to https://www.browserless.io/pricing, a unit
    is a block of browser time up to 30 seconds.

    Attributes:
        browserless_token: Your API token/key for Browserless.io
        browserless_url: A string for remote URL to connect to Browserless.io
                         (default 'wss://chrome.browserless.io/playwright')
        connect_over_cdp: A boolean for connecting via Playwright Chrome
                          DevTools
        page_limit: An integer for number of simultaneous Chrome Pages to use
                    (default 5)
        request_timeout: An integer, in ms, to timeout for each url
                         (default 10000)
    """

    def __init__(
        self,
        browserless_token="1234567890",
        browserless_url="ws://localhost:4321/playwright/chromium",
        connect_over_cdp=False,
        page_limit=5,
        request_timeout=10000,
        preload_pages=False,
    ):
        self.page_limit = page_limit
        self.request_timeout = request_timeout
        self.browserless_token = browserless_token
        self.browserless_url = browserless_url
        self.connect_over_cdp = connect_over_cdp
        self.playwright = None
        self.browser = None
        self.pages = []
        self.preload_pages = preload_pages

    async def __aenter__(self):
        await self.start_browser(preload_pages=self.preload_pages)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.stop_browser()

    async def start_browser(self, preload_pages=None):
        """Starts the browser and initializes pages."""
        if preload_pages is None:
            preload_pages = self.preload_pages
        url = (
            f"{self.browserless_url}"
            f"?token={self.browserless_token}"
            f"&headless=false"
        )
        logger.info(f"start_browser begin for url: {url}")
        self.playwright = await async_playwright().start()

        if self.connect_over_cdp:
            self.browser = await self.playwright.chromium.connect_over_cdp(
                endpoint_url=url
            )
        else:
            self.browser = await self.playwright.chromium.connect(ws_endpoint=url)

        if preload_pages:
            await self._preload_pages()

    async def _preload_pages(self):
        logger.info("browser connected")
        for i in range(self.page_limit):
            page = await self.browser.new_page()
            logger.info(f"start_browser created page {i}")
            self.pages.append((page, i))

    async def stop_browser(self):
        logger.info("stop browser begin")
        for page, page_id in self.pages:
            logger.info(f"closing page_id {page_id}")
            await page.close()
        if self.browser:
            await self.browser.close()

    async def scrape_url(self, page, page_id, url):
        """Scrapes a single URL using a given page."""
        try:
            logger.info(f"scrape_url begin for page_id {page_id}, url {url}")
            await page.goto(url, timeout=self.request_timeout)
            content = await page.content()
            return url, None, content
        except Exception as e:
            logger.exception(f"Error scraping {url}: {e}")
            return url, str(e), None

    async def page_process_queue(self, url_queue, page, page_id, callback):
        """A page instance continuously scrape urls from the queue."""
        logger.info(
            f"page_process_queue begin with page_id {page_id} "
            f"and url_queue length of {url_queue.qsize()}"
        )
        while True:
            if url_queue.empty():
                logger.info(f"page_process_queue queue empty for page_id {page_id}")
                break
            url = await url_queue.get()
            url, error, content = await self.scrape_url(
                page=page, page_id=page_id, url=url
            )
            await callback(url, error, content)

    async def run(self, url_queue, callback):
        """Main method to process and scrape URLs from the queue."""
        logger.info("run begin")
        await self.start_browser(preload_pages=True)
        logger.info("about to run tasks")
        tasks = []
        for page, page_id in self.pages:
            task = asyncio.create_task(
                self.page_process_queue(url_queue, page, page_id, callback)
            )
            tasks.append(task)

        await asyncio.gather(*tasks)
        logger.info("all tasks completed")
        await self.stop_browser()
        logger.info("browser stopped")


async def fill_survey():
    # Prompt user for the 26-digit Survey Number
    CN = input("Enter the 26-digit Survey Number: ")
    if len(CN) != 26 or not CN.isdigit():
        logger.error("Invalid Survey Number. Please ensure it is a 26-digit number.")
        return

    # Split the Survey Number into segments
    CN1 = CN[0:5]
    CN2 = CN[5:10]
    CN3 = CN[10:15]
    CN4 = CN[15:20]
    CN5 = CN[20:25]
    CN6 = CN[25:26]

    logger.info("Survey Number segments:")
    logger.info(
        f"CN1: {CN1}, CN2: {CN2}, CN3: {CN3}, CN4: {CN4}, CN5: {CN5}, CN6: {CN6}"
    )

    # Initialize Playwright and launch the browser
    async with Scraper(page_limit=1, preload_pages=True) as browser:
        logger.info("Launching browser...")
        page, _page_num = browser.pages[0]

        # Maximize the window by setting viewport size
        await page.set_viewport_size({"width": 1920, "height": 1080})
        logger.info("Browser window maximized.")

        # Navigate to the survey page
        survey_url = "https://www.mcdvoice.com/"
        logger.info(f"Navigating to {survey_url}")
        await page.goto(survey_url)

        # Wait for the survey input fields to be visible
        try:
            await page.wait_for_selector("#CN1")
            logger.info("Survey input fields are visible.")
        except Exception as e:
            logger.error(f"Survey input fields did not load: {e}")
            return

        # Fill out the survey inputs
        await page.fill("#CN1", CN1)
        await page.fill("#CN2", CN2)
        await page.fill("#CN3", CN3)
        await page.fill("#CN4", CN4)
        await page.fill("#CN5", CN5)
        await page.fill("#CN6", CN6)
        logger.info("Filled out survey input fields.")

        # Click the "NextButton"
        try:
            await page.click("#NextButton")
            logger.info("Clicked the Next button.")
        except Exception as e:
            logger.error(f"Failed to click the Next button: {e}")
            return

        # Wait for the questions to load
        try:
            await page.wait_for_selector(
                ".question-class"
            )  # Update with actual class name
            logger.info("Questions are loaded.")
        except Exception as e:
            await take_screenshot(page)
            logger.error(f"Questions did not load: {e}")
            return

        # Randomly answer the multiple-choice questions
        questions = await page.query_selector_all(
            ".question-class"
        )  # Update with actual class name
        logger.info(f"Found {len(questions)} questions to answer.")

        for idx, question in enumerate(questions, start=1):
            try:
                options = await question.query_selector_all("input[type='radio']")
                if options:
                    chosen_option = random.choice(options)
                    await chosen_option.check()
                    logger.info(f"Question {idx}: Selected a random option.")
                else:
                    logger.warning(f"Question {idx}: No radio options found.")
            except Exception as e:
                logger.error(f"Error selecting option for question {idx}: {e}")

        # Submit the form
        try:
            await page.click("#submit")  # Ensure the submit button has the correct ID
            logger.info("Clicked the Submit button.")
        except Exception as e:
            await take_screenshot(page)
            logger.error(f"Failed to click the Submit button: {e}")
            return

        # Optionally, wait for a confirmation message or page
        try:
            await page.wait_for_selector(
                "#confirmation"
            )  # Update with actual confirmation selector
            logger.info("Survey submitted successfully.")
        except Exception as e:
            await take_screenshot(page)
            logger.warning(f"Confirmation message not found: {e}")

        await take_screenshot(page)
        # Keep the browser open for a few seconds to observe the result
        await asyncio.sleep(5)

        logger.info("Browser closed.")


async def take_screenshot(page):
    """Takes a screenshot of the current page and saves it with a timestamp."""
    content = await page.content()
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        await page.screenshot(path=f"survey_completion-{timestamp}.png")
        logger.info("Screenshot saved as survey_completion.png")
    except Exception as e:
        logger.error(f"Failed to take screenshot: {e}")
    logger.info(f"Survey submission result: {content}")


def main():
    asyncio.run(fill_survey())


if __name__ == "__main__":
    main()
