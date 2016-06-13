from ast import parse

import pytest

from smother.python import PythonFile
from smother.python import Visitor


case_func = """
def a():
    pass
"""
ctx_func = ['', 'a', 'a']

case_class = """
class A:

    def method(self):
        pass

    x = 3
"""
ctx_class = ['', 'A', 'A', 'A.method', 'A.method', 'A', 'A']

case_decorated_function = """
x = 5

@dec
def a():
    pass
"""
ctx_decorated_function = ['', '', '', 'a', 'a', 'a']

case_inner_func = """

def a():
    def b():
        pass
    x = None
"""
ctx_inner_func = ['', '', 'a', 'a.b', 'a.b', 'a']

case_decorated_method = """
class Foo:
    @dec
    def bar(self):
        pass
"""
ctx_decorated_method = ['', 'Foo', 'Foo.bar', 'Foo.bar', 'Foo.bar']

VISITOR_CASES = [
    (case_func, ctx_func),
    (case_class, ctx_class),
    (case_decorated_function, ctx_decorated_function),
    (case_inner_func, ctx_inner_func),
    (case_decorated_method, ctx_decorated_method),
]


@pytest.mark.parametrize('code,expected', VISITOR_CASES)
def test_visitor(code, expected):
    ast = parse(code)
    visitor = Visitor(prefix='')
    visitor.visit(ast)
    assert visitor.lines == expected


CONTEXT_CASES = [
    (case_func, 'a', (2, 4)),
    (case_class, 'A', (2, 8)),
    (case_class, 'A.method', (4, 6)),
    (case_decorated_method, 'Foo', (2, 6)),
]


@pytest.mark.parametrize("code,context,expected", CONTEXT_CASES)
def test_context_range(code, context, expected):

    pf = PythonFile('test.py', prefix='', source=code)
    print(pf.lines)
    assert pf.context_range(context) == expected


def test_default_prefix():

    assert PythonFile('test.py', source='').prefix == 'test'
    assert PythonFile('a/b/c.py', source='').prefix == 'a.b.c'
    assert PythonFile('a/b/c.pyc', source='').prefix == 'a.b.c'
    assert PythonFile('a/b/c.pyo', source='').prefix == 'a.b.c'
    assert PythonFile('a/b/c.pyw', source='').prefix == 'a.b.c'
    assert PythonFile('a/b/c/__init__.py', source='').prefix == 'a.b.c'