class dsl:
    """Minimal decorator stubs for AST discovery fixtures."""

    def component(fn=None, **_kwargs):
        """Decorator stub for @dsl.component."""

        def deco(f):
            return f

        return deco(fn) if fn is not None else deco

    def pipeline(fn=None, **_kwargs):
        """Decorator stub for @dsl.pipeline."""

        def deco(f):
            return f

        return deco(fn) if fn is not None else deco


@dsl.component
async def comp_async():
    """Sample async component function."""
    return 1


@dsl.pipeline
async def pipe_async():
    """Sample async pipeline function."""
    return 2
