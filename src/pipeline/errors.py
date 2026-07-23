class PipelineStepError(RuntimeError):
    """A step failure with an allowlisted, non-sensitive public explanation."""

    def __init__(self, code, safe_message):
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message
