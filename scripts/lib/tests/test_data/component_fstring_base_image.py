from kfp import dsl

tag = "main"


@dsl.component(base_image=f"quay.io/org/image:{tag}")
def my_component():
    pass
