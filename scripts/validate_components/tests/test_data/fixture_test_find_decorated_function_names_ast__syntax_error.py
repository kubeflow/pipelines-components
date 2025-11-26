"""Fixture source that intentionally fails to parse as Python.

This file itself must remain valid Python (so pytest/ruff can load it). The test writes
`BROKEN_SOURCE` to a temporary `.py` file and points the AST parser at that file.
"""

BROKEN_SOURCE = """def oops(:
    pass

"""
