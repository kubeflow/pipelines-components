from kfp import dsl

@dsl.component
def hello_world(name: str) -> str:
    """Simple greeting component that says hello.
    
    This is a longer description that should not appear in the index.
    
    Args:
        name: Name to greet.
        
    Returns:
        Greeting message.
    """
    return f"Hello {name}!"

