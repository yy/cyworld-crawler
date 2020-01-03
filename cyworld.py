import os
import re
import glob
import time
import logging
import itertools
import requests
import shutil
from pathlib import Path
from datetime import datetime

from tqdm import tqdm
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class CyPost:
    def __init__(self,
                 html_src,
                 content_id,
                 root="./posts",
                 template_f="./template.html"):
        self.root = root
        self.template_f = template_f
        self.content_id = content_id
        self.soup = BeautifulSoup(html_src, "html.parser")
        self.privacy = None
        self.timestamp = None
        self.title = None
        self.dscr = None

    def parse(self):
        self.privacy = self.parse_privacy()
        self.timestamp = self.parse_timestamp()
        self.title = self.parse_title()
        self.dscr = self.parse_dscr()

    def get_basename(self, optional_elms=[], ext="html"):
        base_elms = [
            self.timestamp.strftime("%Y%m%d"),
            re.sub(r"[^a-zA-Z0-9가-힣]", "_", self.title),
            str(self.content_id),
        ]
        elms = base_elms + optional_elms
        return "_".join(elms) + ".{}".format(ext)

    def get_fname(self, dir_for_post):
        basename = self.get_basename(ext="html")
        return os.path.join(dir_for_post, basename)

    def prepare_directory(self):
        dir_for_post = os.path.join(self.root,
                                    self.timestamp.strftime("%Y/%m"))
        Path(dir_for_post).mkdir(parents=True, exist_ok=True)
        return dir_for_post

    def pprint(self):
        print("Title: {}".format(self.title))
        print("Datetime: {}".format(self.timestamp))
        print("Privacy setting: {}".format(self.privacy))
        print()
        print(self.dscr)

    def metadata_list(self):
        return list(
            self.soup.select("div.view1")[0].p.children)[-1].strip().split()

    def is_deleted(self):
        if self.soup.select("div.erorr_page"):
            return True
        return False

    def parse_privacy(self):
        return self.metadata_list()[-1]

    def parse_timestamp(self):
        datetime_str = " ".join(self.metadata_list()[:2])
        timestamp = datetime.strptime(datetime_str, "%Y.%m.%d %H:%M")
        logging.info("Parsed timestamp: {}".format(timestamp))
        return timestamp

    def parse_title(self):
        logging.info(self.soup.h3.string)
        return self.soup.h3.string

    def parse_dscr(self):
        """ description can containo multiple sections, each of which contain
        an image or text"""
        img_cnt = 0
        content = []
        sections = self.soup.select("div.dscr")[0].find_all("section")
        logging.info("# of sections: {}".format(len(sections)))
        for section in sections:
            if "imageBox" in section["class"]:
                try:
                    content.append(self.handle_image(section.img, img_cnt))
                    img_cnt += 1
                except FileNotFoundError:
                    continue
            elif "textBox" in section["class"]:
                content += self.handle_text(section.div.children)
            elif ("bgmBox" in section["class"] or "fontBox" in section["class"]
                  or "urlBox" in section["class"]
                  or "mediaBox" in section["class"]
                  or "fileBox" in section["class"]):
                continue
            else:
                logging.error("unidentified class in section: {}".format(
                    section["class"]))
        return content

    def handle_text(self, paragraphs):
        return [x.string.strip() for x in paragraphs if x.string]

    def handle_image(self, img, img_cnt):
        ext = img["src"].split(".").pop()
        if len(ext) > 4 and ext.startswith("com"):
            raise FileNotFoundError
        res = requests.get(img["src"], stream=True)

        fname = self.get_basename(optional_elms=[str(img_cnt)], ext=ext)
        dir_for_post = self.prepare_directory()

        with open(os.path.join(dir_for_post, fname), "wb") as image:
            shutil.copyfileobj(res.raw, image)

        return '<img src="{}" />'.format(fname)

    def produce_output_html(self):
        template = open(self.template_f).read()
        return (template.replace("{title}", self.title).replace(
            "{timestamp}", self.timestamp.isoformat()).replace(
                "{privacy}", self.privacy).replace("{content}",
                                                   self.text_tohtml()))

    def save(self):
        """ save the post in the root directory. Make a folder for each year
        and month.  """
        output_html = self.produce_output_html()

        dir_for_post = self.prepare_directory()
        fname = self.get_fname(dir_for_post)
        logging.info(fname)

        open(fname, "w").write(output_html)

    def text_tohtml(self):
        return "\n".join("<p>{}</p>".format(x) for x in self.dscr)


class Cyworld:
    def __init__(
            self,
            driver_path="./driver/chromedriver",
            wait=15,
            delay=7,
            content_ids_fname="contents_ids.txt",
            downloaded_cid_set_fname="downloaded.txt",
    ):
        self.driver = webdriver.Chrome(driver_path)
        self.wait = WebDriverWait(self.driver, wait)
        self.delay = delay
        self.base_url = "https://cy.cyworld.com"
        self.user_id = None
        self.content_ids_fname = content_ids_fname
        self.content_ids = self.load_content_ids()
        self.downloaded_cid_set_fname = downloaded_cid_set_fname
        self.downloaded_cids = self.load_downloaded_cid_set()

    def load_content_ids(self):
        if glob.glob(self.content_ids_fname):
            return set(line.strip() for line in open(self.content_ids_fname))
        else:
            return set()

    def save_content_ids(self):
        with open(self.content_ids_fname, "w") as fout:
            for cid in self.content_ids:
                fout.write("{}\n".format(cid))

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

    def get_content_ids_from_current_page(self, offset_idx=0):
        self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "p.btn_list_more")))

        contents = self.driver.find_elements_by_css_selector(
            'input[name="contentID[]"]')[offset_idx:]

        for content in contents:
            cid = content.get_attribute("value")

            logging.info("Number of posts: {}".format(offset_idx + 1))

            self.content_ids.add(cid)
            self.save_content_ids()
            offset_idx += 1

    def content_url_from_cid(self, cid):
        return "{}/home/{}/post/{}/layer".format(self.base_url, self.user_id,
                                                 cid)

    def get_all_content_ids(self):
        while self.driver.find_element_by_css_selector("p.btn_list_more"):
            offset_idx = len(self.content_ids)

            try:
                self.get_content_ids_from_current_page(offset_idx)
                next_button = self.wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "p.btn_list_more")))
                time.sleep(self.delay)
                next_button.click()

            except TimeoutException:
                break

    def load_downloaded_cid_set(self):
        if glob.glob(self.downloaded_cid_set_fname):
            return set(line.strip()
                       for line in open(self.downloaded_cid_set_fname))
        else:
            return set()

    def save_downloaded_cid_set(self):
        with open(self.downloaded_cid_set_fname, "w") as fout:
            fout.write("\n".join(self.downloaded_cids))

    def download_single_content_from_cid(self, cid):
        url = self.content_url_from_cid(cid)
        logging.info("opening a content URL: {}".format(url))

        backoff = 10
        while True:
            self.driver.get(url)
            cp = CyPost(html_src=self.driver.page_source, content_id=cid)
            try:
                cp.parse()
                cp.save()
                break
            except IndexError:
                if backoff > 20 and cp.is_deleted():
                    break

                time.sleep(backoff)
                backoff += 10
                logging.info("retrying...")
                continue

        self.downloaded_cids.add(cid)
        self.save_downloaded_cid_set()

    def download_all_contents(self):
        for cid in tqdm(
                list(
                    itertools.chain(self.downloaded_cids,
                                    self.content_ids - self.downloaded_cids))):
            if cid in self.downloaded_cids:
                continue
            self.download_single_content_from_cid(cid)
            time.sleep(self.delay)
