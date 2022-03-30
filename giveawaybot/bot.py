import argparse
import json
import random

import requests
from loguru import logger


class AniListGiveaway:
    def __init__(self, args):
        self.args = args
        logger.info(f"Getting contestants from {self.args.user}'s followers list")
        self.user_id = self.get_user_id()
        self.contestants = self.get_contestants()
        logger.info(f"Found {len(self.contestants)} contestants")
        logger.info(f"Drawing {self.args.winners} winners")
        self.winners = self.draw_winners()
        logger.info(f"Winner(s): {', '.join(self.winners)}")

    def send_graphql_request(self, query, variables):
        r = requests.post(
            url="https://graphql.anilist.co/",
            json={"query": query, "variables": variables},
        )

        try:
            data = r.json()
        except json.JSONDecodeError:
            logger.error(f"Failed to get GraphQL API data response: {r.text}")
            raise SystemExit

        if self.args.debug:
            logger.debug(f"GraphQL API response: {r.text} [{r.status_code}]")

        if "errors" in data.keys():
            for message in data["errors"]:
                logger.error(
                    f"GraphQL API returned an error: {message['message']} [{r.status_code}]"
                )
            raise SystemExit

        return data

    def get_user_id(self):
        query = """
        query ($user: String) {
            User(name: $user) {
                id
                name
            }
        }
        """
        variables = {"user": self.args.user}
        json = self.send_graphql_request(query=query, variables=variables)
        if self.args.debug:
            logger.debug(
                f"Retrieved {self.args.user}'s internal ID from GraphQL API: {json['data']['User']['id']}"
            )
        return json["data"]["User"]["id"]

    def get_contestants(self):
        query = """
        query ($page: Int, $userId: Int!) {
            Page(page: $page) {
                pageInfo {
                total
                perPage
                currentPage
                lastPage
                hasNextPage
                }
                followers(userId: $userId, sort: USERNAME) {
                name
                }
            }
        }
        """
        contestants = []
        page = 1
        while True:
            variables = {"userId": self.user_id, "page": page}
            json = self.send_graphql_request(query=query, variables=variables)

            if not json["data"]["Page"]["followers"]:
                logger.error(
                    "Either the AniList user ID specified was invalid or the user has no followers"
                )

            if json["data"]["Page"]["pageInfo"]["total"] < self.args.winners:
                logger.error(
                    (
                        f"The amount of winners to be drawn ({self.args.winners}) is higher "
                        f"than the amount of followers ({json['data']['Page']['pageInfo']['total']})"
                    )
                )
                raise SystemExit

            for user in json["data"]["Page"]["followers"]:
                contestants.append(user["name"])

            if page >= json["data"]["Page"]["pageInfo"]["lastPage"]:
                break

            page += 1

        return contestants

    def draw_winners(self):
        return random.sample(population=self.contestants, k=self.args.winners)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-u",
        "--user",
        help="The username of the user to draw contestants from",
        type=str,
        required=True,
    )
    parser.add_argument(
        "-w",
        "--winners",
        help="The amount of winners to be drawn",
        type=int,
        required=True,
    )
    parser.add_argument(
        "-d",
        "--debug",
        help="Run the script in debug mode, logs extra information to console",
        action="store_true",
        required=False,
    )
    args = parser.parse_args()
    AniListGiveaway(args)
