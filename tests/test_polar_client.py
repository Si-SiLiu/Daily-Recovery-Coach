import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src import polar_client


class PolarClientTests(unittest.TestCase):
    def write_tokens(self, directory, **overrides):
        data = {
            "access_token": "access-token-value",
            "refresh_token": "refresh-token-value",
            "expires_at": int(time.time()) + 3600,
        }
        data.update(overrides)
        token_file = Path(directory) / "polar_tokens.json"
        token_file.write_text(json.dumps(data), encoding="utf-8")
        return token_file

    def test_reads_access_token_from_token_file(self):
        with tempfile.TemporaryDirectory() as directory:
            token_file = self.write_tokens(directory)

            client = polar_client.PolarClient(token_file=token_file)

            self.assertEqual(client.tokens["access_token"], "access-token-value")

    def test_detects_expired_token(self):
        with tempfile.TemporaryDirectory() as directory:
            token_file = self.write_tokens(directory, expires_at=int(time.time()) - 1)
            client = polar_client.PolarClient(token_file=token_file)

            self.assertTrue(client.is_token_expired(leeway_seconds=0))

    @patch("src.polar_client.requests.post")
    def test_refresh_access_token_updates_token_file(self, post):
        with tempfile.TemporaryDirectory() as directory:
            token_file = self.write_tokens(directory, expires_at=int(time.time()) - 1)
            response = Mock(status_code=200)
            response.json.return_value = {
                "access_token": "new-access-token",
                "expires_in": 3600,
                "token_type": "bearer",
            }
            post.return_value = response

            with patch.object(polar_client, "CLIENT_ID", "client"), patch.object(
                polar_client, "CLIENT_SECRET", "secret"
            ):
                client = polar_client.PolarClient(token_file=token_file)
                client.refresh_access_token()

            saved = json.loads(token_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["access_token"], "new-access-token")
            self.assertEqual(saved["refresh_token"], "refresh-token-value")
            self.assertIn("expires_at", saved)

    def test_require_valid_token_refreshes_when_expired(self):
        with tempfile.TemporaryDirectory() as directory:
            token_file = self.write_tokens(directory, expires_at=int(time.time()) - 1)
            client = polar_client.PolarClient(token_file=token_file)
            client.refresh_access_token = Mock(return_value=client.tokens)

            client.require_valid_token()

            client.refresh_access_token.assert_called_once_with()

    def test_get_sends_bearer_token_without_printing_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            token_file = self.write_tokens(directory)
            session = Mock()
            response = Mock(status_code=200, text='{"ok": true}')
            response.json.return_value = {"ok": True}
            session.get.side_effect = [
                polar_client.requests.exceptions.SSLError("synthetic transient TLS error"),
                response,
            ]
            client = polar_client.PolarClient(
                token_file=token_file,
                api_base_url="https://example.test/v3",
                session=session,
            )

            with patch("src.polar_client.time.sleep") as sleep:
                result = client.get("/exercises", params={"samples": "false"})

            self.assertEqual(result, {"ok": True})
            self.assertEqual(session.get.call_count, 2)
            sleep.assert_called_once_with(polar_client.GET_RETRY_BACKOFF_SECONDS)
            _, kwargs = session.get.call_args
            self.assertEqual(kwargs["headers"]["Authorization"], "Bearer access-token-value")
            self.assertEqual(kwargs["headers"]["Accept"], "application/json")
            self.assertEqual(kwargs["params"], {"samples": "false"})

    def test_training_sessions_endpoint_params(self):
        with tempfile.TemporaryDirectory() as directory:
            token_file = self.write_tokens(directory)
            session = Mock()
            response = Mock(status_code=200, text="[]")
            response.json.return_value = []
            session.get.return_value = response
            client = polar_client.PolarClient(token_file=token_file, session=session)

            client.get_training_sessions(from_date="2026-07-01", to_date="2026-07-10")

            _, kwargs = session.get.call_args
            self.assertTrue(session.get.call_args.args[0].endswith("/v4/data/training-sessions/list"))
            self.assertEqual(kwargs["params"]["from"], "2026-07-01T00:00:00")
            self.assertEqual(kwargs["params"]["to"], "2026-07-10T23:59:59")

    def test_daily_activity_endpoint_params(self):
        with tempfile.TemporaryDirectory() as directory:
            token_file = self.write_tokens(directory)
            session = Mock()
            response = Mock(status_code=200, text="[]")
            response.json.return_value = []
            session.get.return_value = response
            client = polar_client.PolarClient(token_file=token_file, session=session)

            client.get_daily_activity(
                from_date="2026-07-01",
                to_date="2026-07-10",
            )

            _, kwargs = session.get.call_args
            self.assertTrue(session.get.call_args.args[0].endswith("/v4/data/activity/list"))
            self.assertEqual(kwargs["params"]["from"], "2026-07-01")
            self.assertEqual(kwargs["params"]["to"], "2026-07-10")

    def test_new_v3_endpoint_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            token_file = self.write_tokens(directory)
            session = Mock()
            response = Mock(status_code=200, text="[]")
            response.json.return_value = []
            session.get.return_value = response
            client = polar_client.PolarClient(token_file=token_file, session=session)

            client.get_sleep()
            self.assertTrue(session.get.call_args.args[0].endswith("/v4/data/sleeps"))

            client.get_sleep_for_date("2026-07-08")
            self.assertTrue(session.get.call_args.args[0].endswith("/v4/data/sleeps"))
            _, kwargs = session.get.call_args
            self.assertEqual(kwargs["params"]["from"], "2026-07-08")
            self.assertEqual(kwargs["params"]["to"], "2026-07-09")
            self.assertIn("sleep-evaluation", kwargs["params"]["features"])

            client.get_nightly_recharge()
            self.assertTrue(session.get.call_args.args[0].endswith("/v4/data/nightly-recharge-results"))

            client.get_nightly_recharge(
                from_date="2026-07-01", to_date="2026-07-02", samples=True,
            )
            _, kwargs = session.get.call_args
            self.assertEqual(kwargs["params"]["features"], "samples")

            with self.assertRaises(polar_client.PolarClientError):
                client.get_nightly_recharge(
                    from_date="2026-07-01", to_date="2026-07-10", samples=True,
                )

            client.get_cardio_load()
            self.assertTrue(session.get.call_args.args[0].endswith("/v4/data/cardio-load"))

            client.get_continuous_heart_rate(from_date="2026-07-01", to_date="2026-07-10")
            self.assertTrue(session.get.call_args.args[0].endswith("/v4/data/continuous-samples"))
            _, kwargs = session.get.call_args
            self.assertEqual(kwargs["params"]["from"], "2026-07-01")
            self.assertEqual(kwargs["params"]["to"], "2026-07-10")
            self.assertEqual(kwargs["params"]["features"], ("heart-rate-samples",))


if __name__ == "__main__":
    unittest.main()
