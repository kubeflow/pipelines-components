class dsl:
    """Minimal decorator stubs for compilation validation fixtures."""

    @staticmethod
    def pipeline(fn=None, **kwargs):
        """Decorator stub for @dsl.pipeline."""

        def deco(f):
            return f

        return deco(fn) if fn is not None else deco


@dsl.pipeline
def my_pipeline():
    """Sample pipeline function."""
    return 2
