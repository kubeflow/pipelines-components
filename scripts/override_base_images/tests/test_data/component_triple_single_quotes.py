from kfp import dsl


@dsl.component(base_image='''ghcr.io/kubeflow/pipelines-components-example:main''')
def my_component():
    pass
