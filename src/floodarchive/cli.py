import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--posts", type=int, help="Number of posts to include in the build")

    return parser.parse_args()
