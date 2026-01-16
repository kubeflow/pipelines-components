from kfp import dsl


@dsl.component(base_image="quay.io/org/image1:main")
def component_one():
    pass


@dsl.component(base_image="quay.io/org/image2:main")
def component_two():
    pass
