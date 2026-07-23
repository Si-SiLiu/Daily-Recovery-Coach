"""Shared styling for Streamlit controls used for manual data entry."""


MANUAL_INPUT_CSS = """
<style>
/* Keep manual editing and +/- steppers; hide only the value-clearing affordance. */
div[data-testid="stNumberInput"] button[aria-label*="clear" i],
div[data-testid="stNumberInput"] button[title*="clear" i],
div[data-testid="stNumberInput"] button[data-testid*="clear" i],
div[data-testid="stTextInput"] button[aria-label*="clear" i],
div[data-testid="stTextInput"] button[title*="clear" i],
div[data-testid="stTextInput"] button[data-testid*="clear" i],
div[data-testid="stTextArea"] button[aria-label*="clear" i],
div[data-testid="stTextArea"] button[title*="clear" i],
div[data-testid="stTextArea"] button[data-testid*="clear" i] {
    display: none !important;
}
</style>
"""


def render_manual_input_styles(streamlit):
    """Hide clear buttons in editable text/number controls across every page."""
    streamlit.markdown(MANUAL_INPUT_CSS, unsafe_allow_html=True)
