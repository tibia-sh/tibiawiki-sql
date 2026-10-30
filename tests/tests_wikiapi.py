# Changed by tibia.sh in 2026. See "About this copy" in README.md.
import json
import unittest
from unittest.mock import Mock, call

import requests

from tests import load_resource
from tibiawikisql.api import Article, WikiClient, WikiEntry, Image
from tibiawikisql.errors import WikiApiError


def response(status_code: int, text: str) -> Mock:
    """A stand-in for a `requests.Response` with only an explicit status and text."""
    return Mock(spec=["status_code", "text"], status_code=status_code, text=text)


def revisions_body(titles: list[str]) -> str:
    """A revisions query body holding one article per title."""
    pages = {
        str(page_id): {
            "pageid": page_id,
            "ns": 0,
            "title": title,
            "revisions": [{"timestamp": "2017-04-26T20:04:19Z", "*": f"Content of {title}"}],
        }
        for page_id, title in enumerate(titles, start=1)
    }
    return json.dumps({"query": {"pages": pages}})


class TestWikiApi(unittest.TestCase):

    def setUp(self):
        self.sleep = Mock()
        self.wiki_client = WikiClient(sleep=self.sleep)
        self.session = Mock()
        self.wiki_client.session = self.session

    def respond(self, *outcomes):
        """Make the session answer each request with the next outcome, a response or an exception to raise."""
        self.session.get.side_effect = list(outcomes)

    def assert_requests(self, count: int):
        self.assertEqual(self.session.get.call_count, count)
        for request in self.session.get.call_args_list:
            self.assertEqual(request.args, (WikiClient.ENDPOINT,))
            self.assertEqual(request.kwargs["timeout"], 60)

    def test_category_functions(self):
        json_response = load_resource("response_category_without_continue.json")
        self.respond(*[response(200, json_response)] * 3)
        members = list(self.wiki_client.get_category_members("Spells"))
        self.assertIsInstance(members[0], WikiEntry)
        self.assertEqual(len(members), 8)

        members = list(self.wiki_client.get_category_members("Spells", False))
        self.assertEqual(len(members), 10)

        titles = list(self.wiki_client.get_category_members_titles("Spells"))
        self.assertIsInstance(titles[0], str)
        self.assertEqual(len(titles), 8)
        self.assert_requests(3)
        self.sleep.assert_not_called()

    def test_article_functions(self):
        json_response = load_resource("response_revisions.json")
        self.respond(*[response(200, json_response)] * 2)
        # Response is mocked, so this doesn't affect the output, but this matches the order in the mocked response.
        titles = ["Golden Armor", "Golden Shield"]
        articles = list(self.wiki_client.get_articles(titles))
        self.assertIsInstance(articles[0], Article)
        self.assertEqual(articles[0].title, titles[0])
        self.assertIsNone(articles[1])

        article = self.wiki_client.get_article(titles[0])
        self.assertIsInstance(article, Article)
        self.assertEqual(article.title, titles[0])
        self.assert_requests(2)
        self.sleep.assert_not_called()

    def test_image_functions(self):
        json_response = load_resource("response_image_info.json")
        self.respond(*[response(200, json_response)] * 2)
        # Response is mocked, so this doesn't affect the output, but this matches the order in the mocked response.
        titles = ["Golden Armor.gif", "Golden Shield.gif"]
        images = list(self.wiki_client.get_images_info(titles))
        self.assertIsInstance(images[0], Image)
        self.assertEqual(images[0].file_name, titles[0])
        self.assertIsNone(images[1])

        image = self.wiki_client.get_image_info(titles[0])
        self.assertIsInstance(image, Image)
        self.assertEqual(image.file_name, titles[0])
        self.assertEqual(image.extension, ".gif")
        self.assertEqual(image.clean_name, "Golden Armor")
        self.assert_requests(2)
        self.sleep.assert_not_called()

    def test_empty_body_is_retried(self):
        self.respond(response(200, ""), response(200, load_resource("response_revisions.json")))

        articles = list(self.wiki_client.get_articles(["Golden Armor", "Golden Shield"]))

        self.assertEqual(articles[0].title, "Golden Armor")
        self.assertIsNone(articles[1])
        self.assert_requests(2)
        self.assertEqual(self.sleep.call_args_list, [call(5)])

    def test_server_error_is_retried(self):
        self.respond(response(502, "Bad Gateway"), response(200, load_resource("response_revisions.json")))

        article = self.wiki_client.get_article("Golden Armor")

        self.assertEqual(article.title, "Golden Armor")
        self.assert_requests(2)
        self.assertEqual(self.sleep.call_args_list, [call(5)])

    def test_too_many_requests_is_retried(self):
        self.respond(response(429, "Too Many Requests"), response(200, load_resource("response_revisions.json")))

        article = self.wiki_client.get_article("Golden Armor")

        self.assertEqual(article.title, "Golden Armor")
        self.assert_requests(2)
        self.assertEqual(self.sleep.call_args_list, [call(5)])

    def test_connection_error_is_retried(self):
        self.respond(
            requests.ConnectionError("connection reset"),
            response(200, load_resource("response_category_without_continue.json")),
        )

        members = list(self.wiki_client.get_category_members("Spells"))

        self.assertEqual(len(members), 8)
        self.assert_requests(2)
        self.assertEqual(self.sleep.call_args_list, [call(5)])

    def test_body_cut_short_is_retried(self):
        self.respond(
            requests.exceptions.ChunkedEncodingError("connection broken mid-body"),
            response(200, load_resource("response_revisions.json")),
        )

        article = self.wiki_client.get_article("Golden Armor")

        self.assertEqual(article.title, "Golden Armor")
        self.assert_requests(2)
        self.assertEqual(self.sleep.call_args_list, [call(5)])

    def test_bodies_cut_short_raise_after_five_attempts(self):
        self.respond(*[requests.exceptions.ChunkedEncodingError("connection broken mid-body")] * 5)

        with self.assertRaises(WikiApiError) as context:
            self.wiki_client.get_article("Golden Armor")

        error = context.exception
        self.assertIsNone(error.status)
        self.assertIsNone(error.body)
        self.assertIsInstance(error.__cause__, requests.exceptions.ChunkedEncodingError)
        self.assertIn("Golden Armor", str(error))
        self.assert_requests(5)
        self.assertEqual(self.sleep.call_args_list, [call(5), call(15), call(30), call(60)])

    def test_body_that_is_never_json_raises_after_five_attempts(self):
        body = "<html>" + "x" * 300
        self.respond(*[response(200, body)] * 5)

        with self.assertRaises(WikiApiError) as context:
            self.wiki_client.get_article("Golden Armor")

        error = context.exception
        self.assertEqual(error.status, 200)
        self.assertEqual(error.body, body[:200])
        self.assertIsInstance(error.__cause__, ValueError)
        self.assertIn("status 200", str(error))
        self.assertIn("Golden Armor", str(error))
        self.assert_requests(5)
        self.assertEqual(self.sleep.call_args_list, [call(5), call(15), call(30), call(60)])

    def test_timeouts_raise_after_five_attempts(self):
        self.respond(*[requests.Timeout("read timed out")] * 5)

        with self.assertRaises(WikiApiError) as context:
            self.wiki_client.get_article("Golden Armor")

        error = context.exception
        self.assertIsNone(error.status)
        self.assertIsNone(error.body)
        self.assertIsInstance(error.__cause__, requests.Timeout)
        self.assertIn("no response", str(error))
        self.assertIn("Golden Armor", str(error))
        self.assert_requests(5)
        self.assertEqual(self.sleep.call_args_list, [call(5), call(15), call(30), call(60)])

    def test_not_found_raises_at_once(self):
        self.respond(response(404, "Not Found"))

        with self.assertRaises(WikiApiError) as context:
            self.wiki_client.get_article("Golden Armor")

        error = context.exception
        self.assertEqual(error.status, 404)
        self.assertEqual(error.body, "Not Found")
        self.assertIn("status 404", str(error))
        self.assertIn("Golden Armor", str(error))
        self.assert_requests(1)
        self.sleep.assert_not_called()

    def test_api_error_raises_at_once(self):
        body = json.dumps({"error": {"code": "badtitle", "info": "Bad title \"\"."}})
        self.respond(response(200, body))

        with self.assertRaises(WikiApiError) as context:
            self.wiki_client.get_article("")

        error = context.exception
        self.assertEqual(error.status, 200)
        self.assertEqual(error.body, body)
        self.assertIn("badtitle", str(error))
        self.assert_requests(1)
        self.sleep.assert_not_called()

    def test_articles_of_a_retried_batch_are_yielded_once(self):
        first_batch = [f"Article {n}" for n in range(50)]
        second_batch = [f"Article {n}" for n in range(50, 60)]
        self.respond(
            response(200, revisions_body(first_batch)),
            response(503, "Service Unavailable"),
            response(200, revisions_body(second_batch)),
        )

        titles = [article.title for article in self.wiki_client.get_articles(first_batch + second_batch)]

        self.assertEqual(titles, first_batch + second_batch)
        self.assert_requests(3)
        self.assertEqual(self.sleep.call_args_list, [call(5)])

    def test_images_info_stops_after_not_found(self):
        self.respond(response(404, "Not Found"))

        with self.assertRaises(WikiApiError):
            list(self.wiki_client.get_images_info(["Golden Armor.gif"]))

        self.assert_requests(1)
        self.sleep.assert_not_called()

    def test_images_info_stops_after_retry_budget(self):
        self.respond(*[response(502, "Bad Gateway")] * 5)

        with self.assertRaises(WikiApiError) as context:
            list(self.wiki_client.get_images_info(["Golden Armor.gif"]))

        self.assertEqual(context.exception.status, 502)
        self.assert_requests(5)
        self.assertEqual(self.sleep.call_args_list, [call(5), call(15), call(30), call(60)])
