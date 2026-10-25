import ast
import math
from collections.abc import Callable, Mapping

from partwright_ir.model import Expr

FUNCTIONS: dict[str, Callable[..., float]] = {
    "min": min,
    "max": max,
    "abs": abs,
    "sqrt": math.sqrt,
    "sin": lambda d: math.sin(math.radians(d)),
    "cos": lambda d: math.cos(math.radians(d)),
    "tan": lambda d: math.tan(math.radians(d)),
    "round": round,
}
ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,
    ast.Name,
    ast.Call,
    ast.Load,
    ast.USub,
    ast.UAdd,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.Mod,
    ast.FloorDiv,
)


class ExprError(ValueError):
    pass


def parse(expr: Expr) -> ast.expr:
    if isinstance(expr, int | float):
        return ast.Constant(float(expr))
    try:
        tree = ast.parse(expr.strip(), mode="eval").body
    except SyntaxError as e:
        raise ExprError(f"cannot parse expression {expr!r}") from e
    _check(tree, expr)
    return tree


def names(expr: Expr) -> set[str]:
    return {n.id for n in ast.walk(parse(expr)) if isinstance(n, ast.Name) and n.id not in FUNCTIONS}


def evaluate(expr: Expr, values: Mapping[str, float]) -> float:
    return _eval(parse(expr), values, expr)


def to_python(expr: Expr, table: str = "P") -> str:
    tree = parse(expr)
    if isinstance(tree, ast.Constant):
        return repr(tree.value)
    code = ast.unparse(_Subscripter(table).visit(tree))
    return f"({code})" if isinstance(tree, ast.BinOp | ast.UnaryOp) else code


def _check(node: ast.expr, src: Expr) -> None:
    for n in ast.walk(node):
        if not isinstance(n, ALLOWED_NODES):
            raise ExprError(f"unsupported syntax {type(n).__name__} in {src!r}")
        if isinstance(n, ast.Constant) and not isinstance(n.value, int | float):
            raise ExprError(f"non-numeric constant in {src!r}")
        if isinstance(n, ast.Call) and not (isinstance(n.func, ast.Name) and n.func.id in FUNCTIONS):
            raise ExprError(f"unknown function in {src!r}; allowed: {sorted(FUNCTIONS)}")


def _eval(node: ast.expr, values: Mapping[str, float], src: Expr) -> float:
    match node:
        case ast.Constant(value=int() | float() as v):
            return float(v)
        case ast.Name(id=name):
            if name not in values:
                raise ExprError(f"unknown parameter {name!r} in {src!r}")
            return values[name]
        case ast.UnaryOp(op=ast.USub(), operand=x):
            return -_eval(x, values, src)
        case ast.UnaryOp(operand=x):
            return _eval(x, values, src)
        case ast.BinOp(left=a, op=op, right=b):
            return _binop(op, _eval(a, values, src), _eval(b, values, src), src)
        case ast.Call(func=ast.Name(id=fn), args=args):
            return float(FUNCTIONS[fn](*(_eval(a, values, src) for a in args)))
    raise ExprError(f"cannot evaluate {src!r}")


def _binop(op: ast.operator, a: float, b: float, src: Expr) -> float:
    try:
        match op:
            case ast.Add():
                return a + b
            case ast.Sub():
                return a - b
            case ast.Mult():
                return a * b
            case ast.Div():
                return a / b
            case ast.Pow():
                return float(a**b)
            case ast.Mod():
                return a % b
            case ast.FloorDiv():
                return a // b
    except ZeroDivisionError as e:
        raise ExprError(f"division by zero in {src!r}") from e
    raise ExprError(f"unsupported operator in {src!r}")


class _Subscripter(ast.NodeTransformer):
    def __init__(self, table: str) -> None:
        self.table = table

    def visit_Name(self, node: ast.Name) -> ast.expr:
        if node.id in FUNCTIONS:
            return node
        return ast.Subscript(ast.Name(self.table, ast.Load()), ast.Constant(node.id), ast.Load())
