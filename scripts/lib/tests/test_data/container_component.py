from kfp import dsl


@dsl.container_component(base_image="quay.io/org/container:main")
def my_container_component():
    pass
