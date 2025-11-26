from kfp.dsl import component


@component(base_image="quay.io/org/image:main")
def my_component():
    pass
