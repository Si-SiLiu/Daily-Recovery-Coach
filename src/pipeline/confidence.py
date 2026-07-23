try:
    from src.recovery_confidence import rebuild_confidence
except ImportError:
    from recovery_confidence import rebuild_confidence


def run(context, dry_run=False):
    if dry_run:
        return {"confidence_updated": 0}
    return {"confidence_updated": rebuild_confidence()}
