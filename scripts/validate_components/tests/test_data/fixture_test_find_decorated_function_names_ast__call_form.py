class dsl:
    """Minimal decorator stubs for AST discovery fixtures."""

    def component(fn=None, **_kwargs):
        """Decorator stub for @dsl.component (call form)."""

        def deco(f):
            return f

        return deco(fn) if fn is not None else deco

    def pipeline(fn=None, **_kwargs):
        """Decorator stub for @dsl.pipeline (call form)."""

        def deco(f):
            return f

        return deco(fn) if fn is not None else deco


@dsl.component()
def comp_a():
    """Sample component function."""
    pass


@dsl.pipeline(name="x")
def pipe_a():
    """Sample pipeline function."""
    pass
