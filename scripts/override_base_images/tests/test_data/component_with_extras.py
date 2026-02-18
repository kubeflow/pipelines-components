"""My component."""

from kfp import dsl


@dsl.component(
    base_image="ghcr.io/kubeflow/pipelines-components-example:main",
    packages_to_install=["numpy"],
)
def my_component(value: int) -> str:
    return str(value)
