"""Stable, repeatable scroll positioning for Streamlit interaction reruns."""

from __future__ import annotations

import json


# Every selectable-history page uses the same fast three-stage schedule: an
# immediate post-rerun position plus two lightweight corrections for late
# layout changes. The tolerance makes completed corrections no-ops.
FOCUS_DELAYS_MS = (80, 260, 520)


def render_interaction_focus(components, *, target_id, nonce):
    """Scroll the app viewport to a stable anchor after a selection rerun."""
    script = """
        <script>
        const targetId = __TARGET_ID__;
        const focusKey = __FOCUS_KEY__;
        const delays = __DELAYS__;
        const topOffset = 16;
        const positionTolerance = 2;

        function findContext() {
            let currentWindow = window;
            for (let level = 0; level < 5 && currentWindow; level += 1) {
                try {
                    const document = currentWindow.document;
                    const target = document.getElementById(targetId);
                    if (target) return { currentWindow, document, target };
                    currentWindow = currentWindow.parent;
                } catch (error) {
                    return null;
                }
            }
            return null;
        }

        const initialContext = findContext();
        if (initialContext) initialContext.document.documentElement.dataset.drcFocusKey = focusKey;

        function calibrateFocus() {
            const context = findContext();
            if (!context || context.document.documentElement.dataset.drcFocusKey !== focusKey) return;
            const { currentWindow, document, target } = context;
            const root = [
                ...document.querySelectorAll('[data-testid="stAppViewContainer"], section.stMain, section.main'),
            ].find((element) => element.scrollHeight > element.clientHeight) || document.scrollingElement;
            const offset = target.getBoundingClientRect().top - topOffset;
            if (Math.abs(offset) <= positionTolerance) return;
            if (root && root !== document.scrollingElement && root.scrollTo) {
                root.scrollTo({ top: root.scrollTop + offset, behavior: 'auto' });
            } else if (currentWindow.scrollTo) {
                currentWindow.scrollTo({ top: currentWindow.scrollY + offset, behavior: 'auto' });
            }
        }

        delays.forEach((delay) => setTimeout(calibrateFocus, delay));
        </script>
    """.replace("__TARGET_ID__", json.dumps(str(target_id))).replace(
        "__FOCUS_KEY__", json.dumps(f"{target_id}:{nonce}")
    ).replace("__DELAYS__", json.dumps(FOCUS_DELAYS_MS))
    components.html(script, height=1)
