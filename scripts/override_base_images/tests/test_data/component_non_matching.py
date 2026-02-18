from kfp import dsl


@dsl.component(base_image="python:3.11")
def my_component():
    pass
