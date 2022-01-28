#!/usr/bin/python3

#
# Static web page builder tool from Reddit post data
# Author: Adil Gürbüz (beucismis) <beucismis@tutamail.com>
#

from json import loads
from datetime import datetime as dt
from markdown import markdown
from urllib3 import PoolManager
from jinja2 import Environment, FileSystemLoader


SUBREDDIT = "kopyamakarna"
IGNORE_FLAIRS = ["META", "DUYURU"]
URL = "https://api.pushshift.io/reddit/search/submission"

posts = []
after = 1540846800  # Subreddit created_utc
http = PoolManager()


class StaticPageGenerator:
    def __init__(self):
        self.env = Environment(loader=FileSystemLoader("templates"))

    def render_page(self, last_update_time, posts):
        template = self.env.get_template("post.html")

        with open("index.html", "w+") as file:
            file.write(
                template.render(last_update_time=last_update_time, posts=posts)
            )


while True:
    r = http.request(
        "GET", URL, fields={"subreddit": SUBREDDIT, "after": after, "limit": 100}
    )

    if r.status != 200:
        break
    data = loads(r.data.decode("utf-8"))["data"]
    if not (len(data)):
        break
    after = data[-1]["created_utc"]

    for i in range(len(data)):
        if data[i].get("link_flair_text", "") in IGNORE_FLAIRS:
            continue

        title = data[i]["title"]
        selftext = markdown(data[i].get("selftext", ""))
        created = dt.fromtimestamp(data[i]["created_utc"]).ctime()
        full_link = data[i]["full_link"]

        posts.append(
            {
                "title": title,
                "selftext": selftext,
                "created": created,
                "full_link": full_link,
            }
        )


if __name__ == "__main__":
    generator = StaticPageGenerator()
    generator.render_page(dt.now().ctime(), posts[::-1])  # Reverse list
