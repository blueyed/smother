"""
Module for parsing python code
"""
import os
import re
import sys
from ast import iter_child_nodes
from ast import NodeVisitor
from ast import parse


SUFFIX_RE = re.compile('/?(__init__)?\.py[cwo]?')


class InvalidPythonFile(ValueError):
    pass


class Visitor(NodeVisitor):
    """
    Walk a module's ast. Build a `lines` list whose value at each
    index is a context block name for the corresponding source code line.
    """
    def __init__(self, prefix=''):
        """
        Parameters
        ----------
        prefix : str
            The name to give to the module-level context.
        """
        self.line = 1  # which line (1-based) do we populate next?

        # a stack of nested contexts
        self.context = [prefix] if prefix else []
        self.current_context = prefix

        self.lines = []

    def _filldown(self, lineno):
        """
        Copy current_context into `lines` down up until lineno
        """
        if self.line > lineno:
            return  # XXX decorated functions make us jump backwards. understand this more

        self.lines.extend(
            self.current_context for _ in range(self.line, lineno))
        self.line = lineno

    def _add_section(self, node):
        """
        Register the current node as a new context block
        """
        self._filldown(node.lineno)

        # push a new context onto stack
        self.context.append(node.name)
        old_context = self.current_context
        self.current_context = '.'.join(self.context)

        for _ in map(self.visit, iter_child_nodes(node)):
            pass

        # restore current context
        self.context.pop()
        self.current_context = old_context

    def generic_visit(self, node):
        if hasattr(node, 'lineno'):
            self._filldown(node.lineno + 1)

        for _ in map(self.visit, iter_child_nodes(node)):
            pass

    def visit_Module(self, node):
        # need to manually insert one line for empty modules like __init__.py
        if not node.body:
            self.lines = [self.current_context]
        else:
            self.generic_visit(node)


    visit_ClassDef = _add_section
    visit_FunctionDef = _add_section
    visit_AsyncFunctionDef = _add_section


class PythonFile(object):
    """
    A file of python source.
    """
    def __init__(self, filename, source=None, prefix=None):
        """
        Parameters
        ----------
        filename : str
            The path to the file
        source : str (optional)
            The contents of the file. Will be read from `filename`
            if not provided.
        prefix : str (optional)
            Name to give to the outermost context in the file.
            If not provided, will be the "." form of filename
            (ie a/b/c.py -> a.b.c)
        """
        self.filename = filename
        if prefix is None:
            prefix = SUFFIX_RE.sub('', self.filename).replace('/', '.')

        if source is None:
            with open(filename) as infile:
                self.source = infile.read()
        else:
            self.source = source

        try:
            self.ast = parse(self.source)
        except SyntaxError:
            raise InvalidPythonFile(self.filename)

        visitor = Visitor(prefix=prefix)
        visitor.visit(self.ast)
        self.lines = visitor.lines
        self.prefix = prefix

    @classmethod
    def from_modulename(cls, module_name):
        """
        Build a PythonFile given a dotted module name like a.b.c
        """
        # XXX make this more robust (pyc files? zip archives? etc)
        path = module_name.replace('.', '/') + '.py'

        # always search from current directory
        for base in [''] + sys.path:
            fullpath = os.path.join(base, path)
            if os.path.exists(fullpath):
                return cls(fullpath, prefix=module_name)
        else:
            raise ValueError("Module not found: %s" % module_name)

    @property
    def line_count(self):
        return len(self.lines)

    def context_range(self, context):
        """
        Return the 1-offset, right-open range of lines spanned by
        a particular context name.

        Parameters
        ----------
        context : str

        Raises
        ------
        ValueError, if context is not present in the file.
        """
        if not context.startswith(self.prefix):
            context = self.prefix + '.' + context

        lo = hi = None
        for idx, line_context in enumerate(self.lines, 1):

            # context is hierarchical -- context spans itself
            # and any suffix.
            if line_context.startswith(context):
                lo = lo or idx
                hi = idx

        if lo is None:
            raise ValueError("Context %s does not exist in file %s" %
                             (context, self.filename))

        return lo, hi + 1


if __name__ == "__main__":
    # Report contexts of this file
    path = sys.argv[1] if len(sys.argv) == 2 else __file__
    pf = PythonFile(path)
    for section, line in zip(pf.lines, pf.source.splitlines()):
        if len(section) > 40:
            section = '...' + section[-37:]
        print("%40.40s\t %s" % (section, line))