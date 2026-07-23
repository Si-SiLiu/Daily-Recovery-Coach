import re
import unittest
from urllib.parse import parse_qs, urlparse

from src import polar_oauth


class PolarOAuthTests(unittest.TestCase):
    def setUp(self):
        self.original_client_id = polar_oauth.CLIENT_ID
        self.original_client_secret = polar_oauth.CLIENT_SECRET
        self.original_redirect_uri = polar_oauth.REDIRECT_URI
        polar_oauth.app.config["TESTING"] = True
        self.client = polar_oauth.app.test_client()

    def tearDown(self):
        polar_oauth.CLIENT_ID = self.original_client_id
        polar_oauth.CLIENT_SECRET = self.original_client_secret
        polar_oauth.REDIRECT_URI = self.original_redirect_uri

    def test_index_reports_missing_polar_config(self):
        polar_oauth.CLIENT_ID = None
        polar_oauth.CLIENT_SECRET = None

        response = self.client.get("/")

        self.assertEqual(response.status_code, 503)
        body = response.get_data(as_text=True)
        self.assertIn("POLAR_CLIENT_ID", body)
        self.assertIn("POLAR_CLIENT_SECRET", body)

    def test_index_builds_authorization_link_without_exposing_secret(self):
        polar_oauth.CLIENT_ID = "test-client-id"
        polar_oauth.CLIENT_SECRET = "test-client-secret"
        polar_oauth.REDIRECT_URI = "http://localhost:5000/oauth2_callback"

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertNotIn("test-client-secret", body)

        href_match = re.search(r'href="([^"]+)"', body)
        self.assertIsNotNone(href_match)
        url = urlparse(href_match.group(1))
        query = parse_qs(url.query)

        self.assertEqual(url.scheme, "https")
        self.assertEqual(url.netloc, "auth.polar.com")
        self.assertEqual(query["client_id"], ["test-client-id"])
        self.assertEqual(query["response_type"], ["code"])
        self.assertEqual(query["redirect_uri"], ["http://localhost:5000/oauth2_callback"])
        self.assertEqual(
            query["scope"],
            [
                "training_sessions:read activity:read sleep:read "
                "nightly_recharge:read continuous_samples:read profile:read "
                "sports:read"
            ],
        )
        self.assertIn("state", query)

    def test_callback_rejects_state_mismatch_before_token_request(self):
        polar_oauth.CLIENT_ID = "test-client-id"
        polar_oauth.CLIENT_SECRET = "test-client-secret"

        with self.client.session_transaction() as flask_session:
            flask_session["oauth_state"] = "expected-state"

        response = self.client.get("/oauth2_callback?code=test-code&state=wrong-state")

        self.assertEqual(response.status_code, 200)
        self.assertIn("State", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
