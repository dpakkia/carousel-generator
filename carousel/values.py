"""Value resolution for style JSON.

Numbers in a recipe are rarely constants — they are "the right margin", "just
below the last block", "a third of the way down". Rather than force authors to
precompute pixels, any numeric field accepts:

    560                     a literal
    "W - MX"                an arithmetic expression over the slide's variables
    "MX + PAD"
    {"after": 24}           24px below wherever the previous text block ended
    {"of": "H", "mul": 0.5} a fraction of a variable

Expressions are parsed with `ast` and evaluated against a whitelist of nodes,
so a style file can do arithmetic but cannot call code.
"""
import ast
import operator

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_CMP = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne,
    ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.Gt: operator.gt, ast.GtE: operator.ge,
}
_FUNCS = {"min": min, "max": max, "abs": abs, "round": round, "int": int}


class ExpressionError(ValueError):
    """A style file contained an expression that could not be evaluated."""


def evaluate(expr, variables):
    """Evaluate an arithmetic/comparison expression against `variables`."""
    try:
        tree = ast.parse(str(expr), mode="eval")
    except SyntaxError as e:
        raise ExpressionError(f"cannot parse {expr!r}: {e}") from None
    return _eval(tree.body, variables, expr)


def _eval(node, env, src):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, bool)):
            return node.value
        raise ExpressionError(f"{src!r}: only numbers are allowed as literals")
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        raise ExpressionError(f"{src!r}: unknown variable {node.id!r}")
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        return _BINOPS[type(node.op)](_eval(node.left, env, src),
                                      _eval(node.right, env, src))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand, env, src))
    if isinstance(node, ast.BoolOp):
        vals = [_eval(v, env, src) for v in node.values]
        return all(vals) if isinstance(node.op, ast.And) else any(vals)
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        op = _CMP.get(type(node.ops[0]))
        if op:
            return op(_eval(node.left, env, src), _eval(node.comparators[0], env, src))
    if isinstance(node, ast.IfExp):
        return _eval(node.body if _eval(node.test, env, src) else node.orelse, env, src)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id in _FUNCS:
        return _FUNCS[node.func.id](*[_eval(a, env, src) for a in node.args])
    raise ExpressionError(f"{src!r}: unsupported expression")


def number(value, variables, default=None):
    """Resolve any numeric field from a recipe to a float."""
    if value is None:
        return default
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(evaluate(value, variables))
    if isinstance(value, dict):
        if "after" in value:
            return float(variables.get("cursor", 0)) + number(value["after"], variables, 0)
        if "of" in value:
            base = number(value["of"], variables, 0)
            return base * number(value.get("mul", 1), variables, 1) \
                + number(value.get("add", 0), variables, 0)
        raise ExpressionError(f"unrecognised value object: {value!r}")
    raise ExpressionError(f"cannot resolve {value!r} as a number")


def integer(value, variables, default=None):
    n = number(value, variables, default)
    return None if n is None else int(round(n))


def box(value, variables):
    """Resolve a [x0, y0, x1, y1] box, each entry itself an expression."""
    if value is None:
        return None
    return [number(v, variables) for v in value]


def truthy(value, variables, default=True):
    """Resolve a `when:` guard."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return bool(evaluate(value, variables))
