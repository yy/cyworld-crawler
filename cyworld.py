import glob
import time
import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class Cyworld:
    def __init__(
            self,
            driver_path="./driver/chromedriver",
            wait=10,
            delay=5,
            content_urls_fname="contents_urls.txt",
    ):
        self.driver = webdriver.Chrome(driver_path)
        self.wait = WebDriverWait(self.driver, wait)
        self.delay = delay
        self.base_url = "https://cy.cyworld.com"
        self.user_id = None
        self.content_urls_fname = content_urls_fname
        self.content_urls = self.load_content_urls()

    def load_content_urls(self):
        if glob.glob(self.content_urls_fname):
            return set(line.strip() for line in open(self.content_urls_fname))
        else:
            return []

    def save_content_urls(self):
        with open(self.content_urls_fname, "w") as fout:
            for url in self.content_urls:
                fout.write("{}\n".format(url))

    def login(self, email, password):
        logging.info("Opening cyworld homepage...")
        self.driver.get(self.base_url)
        curr_url = self.driver.current_url

        logging.info("logging in...")
        self.driver.find_element_by_name("email").send_keys(email)
        self.driver.find_element_by_name("passwd").send_keys(
            password, Keys.RETURN)
        self.wait.until(EC.url_changes(curr_url))

    def move_to_home(self):
        logging.info("Extracting user id...")
        curr_url = self.driver.current_url
        profile = self.driver.find_element_by_css_selector("a.freak1")
        self.user_id = profile.get_attribute("href").split("/").pop()
        logging.info("userid: %s", self.user_id)

        logging.info("Moving to the homepage...")
        self.driver.find_element_by_id("imggnbuser").click()
        self.wait.until(EC.url_changes(curr_url))

    def get_content_urls_from_current_page(self, offset_idx=0):
        # wait for the "see more" button
        self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "p.btn_list_more")))

        contents = self.driver.find_elements_by_css_selector(
            'input[name="contentID[]"]')[offset_idx:]

        for content in contents:
            cid = content.get_attribute("value")
            content_url = "{}/home/{}/post/{}/layer".format(
                self.base_url, self.user_id, cid)

            logging.info("Number of posts: {}".format(offset_idx + 1))

            self.content_urls.add(content_url)
            self.save_content_urls()
            offset_idx += 1

    def get_all_content_urls(self):
        while self.driver.find_element_by_css_selector("p.btn_list_more"):
            # If we have collected 20 urls, the offset idx = 20. slicing [20:]
            # will give us the next urls.
            offset_idx = len(self.content_urls)

            try:
                self.get_content_urls_from_current_page(offset_idx)
                next_button = self.wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "p.btn_list_more")))
                time.sleep(self.delay)
                next_button.click()

            except TimeoutException:
                break
