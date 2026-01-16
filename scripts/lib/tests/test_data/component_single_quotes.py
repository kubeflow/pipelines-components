from kfp import dsl


@dsl.component(base_image='image:main')
def f():
    pass
