from kfp import dsl


@dsl.component
def no_docs(text: str) -> str:  # noqa: D103
    return text
