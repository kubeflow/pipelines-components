from kfp import dsl


@dsl.component(base_image='ghcr.io/kubeflow/pipelines-components-x:main')
def f():
    pass
