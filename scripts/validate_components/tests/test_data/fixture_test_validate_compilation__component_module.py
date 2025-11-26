from __future__ import annotations


class _Spec:
    def save(self, path: str) -> None:
        """Write a small marker file to simulate KFP spec output."""
        with open(path, "w") as f:
            f.write("ok")


class dsl:
    """Minimal decorator stubs for compilation validation fixtures."""

    @staticmethod
    def component(fn=None, **kwargs):
        """Decorator stub for @dsl.component."""

        def deco(f):
            f.component_spec = _Spec()
            return f

        return deco(fn) if fn is not None else deco

    @staticmethod
    def notebook_component(fn=None, **kwargs):
        """Decorator stub for @dsl.notebook_component."""

        def deco(f):
            f.component_spec = _Spec()
            return f

        return deco(fn) if fn is not None else deco


@dsl.component
def my_component():
    """Sample component function."""
    return 1


@dsl.notebook_component
def my_notebook_component():
    """Sample notebook component function."""
    return 3
