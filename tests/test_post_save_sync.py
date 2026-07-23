import unittest
from unittest import mock

from src.post_save_sync import BASE_DIR, start_recovery_post_save_sync


class PostSaveSyncTests(unittest.TestCase):
    @mock.patch("src.post_save_sync.subprocess.Popen")
    def test_starts_canonical_manual_sync_in_background(self, popen):
        popen.return_value.pid = 4321
        self.assertEqual(start_recovery_post_save_sync(), 4321)
        args, kwargs = popen.call_args
        self.assertEqual(args[0][-2:], ["--trigger-type", "manual"])
        self.assertEqual(kwargs["cwd"], BASE_DIR)
        self.assertTrue(kwargs["start_new_session"])


if __name__ == "__main__":
    unittest.main()
