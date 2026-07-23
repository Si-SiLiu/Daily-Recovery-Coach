import unittest

from src.ui_scroll import FOCUS_DELAYS_MS, render_interaction_focus


class _Components:
    def __init__(self):
        self.calls = []

    def html(self, script, **kwargs):
        self.calls.append((script, kwargs))


class InteractionFocusTests(unittest.TestCase):
    def test_shared_focus_uses_fixed_schedule_nonce_guard_and_tolerance(self):
        components = _Components()
        render_interaction_focus(
            components,
            target_id="recovery-history-situation",
            nonce=7,
        )
        self.assertEqual(len(components.calls), 1)
        script, kwargs = components.calls[0]
        self.assertIn('"recovery-history-situation"', script)
        self.assertIn('"recovery-history-situation:7"', script)
        self.assertIn(str(list(FOCUS_DELAYS_MS)), script)
        self.assertIn("dataset.drcFocusKey", script)
        self.assertIn("positionTolerance = 2", script)
        self.assertIn("Math.abs(offset) <= positionTolerance", script)
        self.assertEqual(kwargs, {"height": 1})


if __name__ == "__main__":
    unittest.main()
