import json
import time
from datetime import datetime as dt
from pathlib import Path
from typing import Dict, List

import requests
from jinja2 import Environment, FileSystemLoader
from markdown import markdown

LIMIT = 100
SORT = "asc"
SUBREDDIT = "kopyamakarna"
DEFAULT_AFTER = 1540846800
POSTS_DB_FILE = "posts.json"
IGNORE_FLAIRS = ["META", "DUYURU"]
API_BASE_URL = "https://api.pullpush.io"


def load_posts() -> List[Dict]:
    try:
        with open(POSTS_DB_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_posts(posts: List[Dict]) -> None:
    with open(POSTS_DB_FILE, "w+") as f:
        json.dump(posts, f, indent=2)


class StaticPageGenerator:
    def __init__(self) -> None:
        script_dir = Path(__file__).parent
        template_dir = script_dir / "templates"
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def render_page(self, submissions: List[Dict]) -> None:
        template = self.env.get_template("post.html")

        with open("index.html", "w+") as file:
            file.write(template.render(last_build_date=time.ctime(), submissions=submissions))


def main() -> None:
    all_submissions = load_posts()
    after = all_submissions[-1]["created_utc"] if all_submissions else DEFAULT_AFTER
    print(f"Loaded {len(all_submissions)} existing posts.")

    while True:
        previous_after = after
        print(f"Fetching new data after: {dt.fromtimestamp(after).isoformat()}")
        response = requests.get(
            API_BASE_URL + "/reddit/search/submission",
            params={
                "subreddit": SUBREDDIT,
                "after": after,
                "limit": LIMIT,
                "sort": SORT,
            },
        )

        if response.status_code != 200:
            print(f"Failed with status code: {response.status_code}")
            if response.status_code == 429:
                print("Rate limit exceeded, sleeping for 60 seconds...")
                time.sleep(60)
                continue
            break

        new_batch = response.json().get("data", [])
        print(f"Found {len(new_batch)} new submissions.")

        if not new_batch:
            break

        for submission in new_batch:
            if any(p.get("url") == submission.get("url") for p in all_submissions):
                continue

            selftext = markdown(submission.get("selftext", ""))
            if selftext.strip() in "<p>[removed]</p>":
                continue
            if submission.get("link_flair_text", "") in IGNORE_FLAIRS:
                continue

            submission["created"] = dt.fromtimestamp(submission.get("created_utc")).ctime()
            all_submissions.append(submission)

        after = all_submissions[-1]["created_utc"]

        if after <= previous_after:
            print("Timestamp not advancing, incrementing by 1 to break loop.")
            after += 1

    print(f"Total posts: {len(all_submissions)}. Saving to {POSTS_DB_FILE}.")
    save_posts(all_submissions)

    generator = StaticPageGenerator()
    generator.render_page(all_submissions[::-1])
    print("Static page generated successfully.")


if __name__ == "__main__":
    main()
