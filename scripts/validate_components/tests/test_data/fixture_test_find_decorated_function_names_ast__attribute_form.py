class dsl:
    """Minimal decorator stubs for AST discovery fixtures."""

    def component(fn=None, **_kwargs):
        """Decorator stub for @dsl.component."""

        def deco(f):
            return f

        return deco(fn) if fn is not None else deco

    def container_component(fn=None, **_kwargs):
        """Decorator stub for @dsl.container_component."""

        def deco(f):
            return f

        return deco(fn) if fn is not None else deco

    def notebook_component(fn=None, **_kwargs):
        """Decorator stub for @dsl.notebook_component."""

        def deco(f):
            return f

        return deco(fn) if fn is not None else deco

    def pipeline(fn=None, **_kwargs):
        """Decorator stub for @dsl.pipeline."""

        def deco(f):
            return f

        return deco(fn) if fn is not None else deco


@dsl.component
def comp_a():
    """Sample component function."""
    pass


@dsl.container_component
def comp_b():
    """Sample container component function."""
    pass


@dsl.notebook_component
def comp_c():
    """Sample notebook component function."""
    pass


@dsl.pipeline
def pipe_a():
    """Sample pipeline function."""
    pass
