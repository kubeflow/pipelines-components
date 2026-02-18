import kfp


@kfp.dsl.component(base_image="quay.io/org/image:main")
def my_component():
    pass
