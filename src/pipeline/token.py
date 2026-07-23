from pathlib import Path

try:
    from src.polar_client import PolarClient, TOKEN_FILE
except ImportError:
    from polar_client import PolarClient, TOKEN_FILE


def run(context, dry_run=False, client_factory=PolarClient, token_file=TOKEN_FILE):
    token_file = Path(token_file)
    if not token_file.exists():
        raise RuntimeError("Polar authorization is required before sync.")
    if dry_run:
        return {"token_available": True, "refresh_required": "not_checked"}

    client = client_factory()
    refresh_required = client.is_token_expired()
    if refresh_required:
        client.require_valid_token()
    context["polar_client"] = client
    return {
        "token_available": True,
        "refresh_required": refresh_required,
        "refreshed": refresh_required,
    }
