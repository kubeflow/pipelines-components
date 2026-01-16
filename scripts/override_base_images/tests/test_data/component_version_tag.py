from kfp import dsl


@dsl.component(base_image="ghcr.io/kubeflow/pipelines-components-example:v1.0.0")
def my_component():
    pass
