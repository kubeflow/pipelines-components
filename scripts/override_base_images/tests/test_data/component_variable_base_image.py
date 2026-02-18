from kfp import dsl

IMAGE = "ghcr.io/kubeflow/pipelines-components-example:main"


@dsl.component(base_image=IMAGE)
def my_component():
    pass
