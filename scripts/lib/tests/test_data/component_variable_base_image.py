from kfp import dsl

IMAGE = "quay.io/org/image:main"


@dsl.component(base_image=IMAGE)
def my_component():
    pass
