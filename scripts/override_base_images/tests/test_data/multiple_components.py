from kfp import dsl


@dsl.component(base_image="ghcr.io/kubeflow/pipelines-components-first:main")
def first():
    pass


@dsl.component(base_image="ghcr.io/kubeflow/pipelines-components-second:main")
def second():
    pass
