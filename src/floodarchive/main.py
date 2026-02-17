import json
import time
from datetime import datetime as dt
from pathlib import Path
from typing import Dict, List

import requests
from jinja2 import Environment, FileSystemLoader
from markdown import markdown

from floodarchive.cli import parse_args

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
    args = parse_args()
    all_submissions = load_posts()
    all_submissions = [p for p in all_submissions if p.get("selftext", "").strip()]
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
            if response.status_code == 429:
                print("Rate limit exceeded, sleeping for 60 seconds...")
                time.sleep(60)
                continue

            raise Exception(f"Failed with status code: {response.status_code}")

        new_batch = response.json().get("data", [])
        print(f"Found {len(new_batch)} new submissions.")

        if not new_batch:
            break

        for submission in new_batch:
            if any(p.get("url") == submission.get("url") for p in all_submissions):
                continue
            if submission.get("link_flair_text", "") in IGNORE_FLAIRS:
                continue
            if "[removed]" in submission.get("selftext", ""):
                continue
            if not submission.get("selftext", "").strip():
                continue

            clean_submission = {
                "title": submission.get("title"),
                "url": submission.get("url"),
                "created_utc": submission.get("created_utc"),
                "selftext": submission.get("selftext", ""),
            }
            all_submissions.append(clean_submission)

        after = all_submissions[-1]["created_utc"]

        if after <= previous_after:
            print("Timestamp not advancing, incrementing by 1 to break loop.")
            after += 1

    print(f"Total posts: {len(all_submissions)}. Saving to {POSTS_DB_FILE}.")
    save_posts(all_submissions)

    if args.posts:
        print(f"Limiting to {args.posts} posts.")
        all_submissions = all_submissions[: args.posts]

    submissions_for_template = []

    for post in all_submissions:
        submissions_for_template.append(
            {
                **post,
                "created": dt.fromtimestamp(post.get("created_utc")).ctime(),
                "selftext": markdown(post.get("selftext", "")),
            }
        )

    generator = StaticPageGenerator()
    generator.render_page(submissions_for_template[::-1])
    print("Static page generated successfully.")


if __name__ == "__main__":
    main()
