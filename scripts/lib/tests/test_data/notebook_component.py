from kfp import dsl


@dsl.notebook_component(base_image="quay.io/org/notebook:main")
def my_notebook_component():
    pass
