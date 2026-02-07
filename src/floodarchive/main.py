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
IGNORE_FLAIRS = ["META", "DUYURU"]
STATE_FILE = "floodarchive_state.json"
API_BASE_URL = "https://api.pullpush.io"


def load_last_after() -> int:
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            return data.get("after", DEFAULT_AFTER)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_AFTER


def save_last_after(timestamp: int) -> None:
    with open(STATE_FILE, "w+") as f:
        json.dump({"after": timestamp}, f)


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
    after = load_last_after()
    all_submissions = []

    while True:
        previous_after = after
        print(f"Fetching data after: {dt.fromtimestamp(after).isoformat()}")
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

        submissions = response.json().get("data", [])
        print(f"Found {len(submissions)} submissions.")

        if not submissions:
            break

        after = submissions[-1]["created_utc"]

        if after <= previous_after:
            print("Timestamp not advancing, incrementing by 1 to break loop.")
            after += 1

        for submission in submissions:
            if submission.get("link_flair_text", "") in IGNORE_FLAIRS:
                continue

            selftext = markdown(submission.get("selftext", ""))

            if selftext.strip() in "<p>[removed]</p>":
                continue

            all_submissions.append(
                {
                    "title": submission.get("title"),
                    "selftext": selftext,
                    "url": submission.get("url"),
                    "created": dt.fromtimestamp(submission.get("created_utc")).ctime(),
                }
            )

    print(f"Saving last timestamp to state file: {dt.fromtimestamp(after).isoformat()}")
    save_last_after(after)

    generator = StaticPageGenerator()
    generator.render_page(all_submissions[::-1])


if __name__ == "__main__":
    main()
