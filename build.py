#!/usr/bin/python3

#
# Static web page builder tool from Reddit post data
# Author: beucismis <beucismis@tutamail.com>
#

from time import ctime
from json import loads
from typing import List, Dict
from datetime import datetime as dt

from markdown import markdown
from urllib3 import PoolManager
from jinja2 import Environment, FileSystemLoader


LIMIT = 100
SUBREDDIT = "kopyamakarna"
IGNORE_FLAIRS = ["META", "DUYURU"]
API_BASE_URL = "https://api.pushshift.io/reddit/search/submission"

after = 1540846800  # Subreddit created_utc
all_submissions = []
http = PoolManager()


class StaticPageGenerator:
    def __init__(self):
        self.env = Environment(loader=FileSystemLoader("templates"))

    def render_page(self, submissions: List[Dict]):
        template = self.env.get_template("post.html")

        with open("index.html", "w+") as file:
            file.write(
                template.render(
                    last_build_date=ctime(), submissions=submissions
                )
            )


while True:
    response = http.request(
        "GET", API_BASE_URL, fields={
            "subreddit": SUBREDDIT, "after": after, "limit": LIMIT
        }
    )

    if response.status != 200:
        break
    submissions = loads(response.data.decode("utf-8"))["data"]
    if not len(submissions):
        break
    after = submissions[-1]["created_utc"]

    for submission in submissions:
        if submission.get("link_flair_text", "") in IGNORE_FLAIRS:
            continue

        selftext = markdown(
            submission.get("selftext", "")
        )
        if selftext.strip() in "<p>[removed]</p>":
            continue

        all_submissions.append(
            {
                "title": submission.get("title"),
                "selftext": selftext,
                "full_link": submission.get("full_link"),
                "created": dt.fromtimestamp(
                    submission.get("created_utc")
                ).ctime(),
            }
        )

        print(submission.get("title"))


if __name__ == "__main__":
    generator = StaticPageGenerator()
    generator.render_page(all_submissions[::-1])
