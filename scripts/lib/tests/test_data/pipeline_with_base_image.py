from kfp import dsl


@dsl.pipeline(base_image="quay.io/org/pipeline-image:main")
def my_pipeline():
    pass
