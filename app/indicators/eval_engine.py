import ast

ALLOWED_NODES = {
    ast.Expression, ast.Call, ast.BinOp, ast.UnaryOp, ast.Name, ast.Load,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.USub,
    ast.Constant, ast.Tuple, ast.List,
    ast.ListComp, ast.comprehension
}


class ExpressionValidator(ast.NodeVisitor):
    def __init__(self, allowed_funcs, allowed_vars):
        self.allowed_funcs = allowed_funcs
        self.allowed_vars = allowed_vars
        self.local_vars = set()

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only function calls allowed")
        fname = node.func.id
        if fname not in self.allowed_funcs:
            raise ValueError(f"Function '{fname}' not registered")
        for arg in node.args:
            self.visit(arg)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):  # using a variable
            if node.id not in self.allowed_vars and node.id not in self.local_vars:
                raise ValueError(f"Unknown variable '{node.id}'")
        elif isinstance(node.ctx, ast.Store):  # defining a variable
            self.local_vars.add(node.id)

    def visit_ListComp(self, node):
            for gen in node.generators:
                self.visit(gen)      # visit_comprehension will add loop var
            self.visit(node.elt)





    def visit_comprehension(self, node):
        # explicitly register loop variable (f in "for f in fib_levels")
        if isinstance(node.target, ast.Name):
            self.local_vars.add(node.target.id)
        self.visit(node.iter)
        for if_clause in node.ifs:
            self.visit(if_clause)

    def generic_visit(self, node):
        if type(node) not in ALLOWED_NODES:
            raise ValueError(f"Disallowed syntax: {ast.dump(node)}")
        super().generic_visit(node)


def validate_expr(expr: str, funcs: dict, vars: list[str]):
    """Validate expression AST: allowed functions + allowed variables"""
    tree = ast.parse(expr, mode="eval")
    ExpressionValidator(funcs, vars).visit(tree)



class SafeEval(ast.NodeVisitor):
    def __init__(self, env, registry):
        self.env = env
        self.registry = registry

    def visit_Call(self, node):
        fname = node.func.id
        args = [self.visit(a) for a in node.args]
        result = self.registry[fname](*args)
        return result


    def visit_Name(self, node):
        return self.env[node.id]

    def visit_Constant(self, node):
        return node.value

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.Add): return left + right
        if isinstance(node.op, ast.Sub): return left - right
        if isinstance(node.op, ast.Mult): return left * right
        if isinstance(node.op, ast.Div): return left / right
        if isinstance(node.op, ast.Pow): return left ** right
        raise ValueError("Unsupported operator")

    def visit_UnaryOp(self, node):
        val = self.visit(node.operand)
        if isinstance(node.op, ast.USub): return -val
        return val
    
    def visit_ListComp(self, node):
        results = []
        saved_env = self.env.copy()

        for gen in node.generators:
            iterable = self.visit(gen.iter)
            for val in iterable:
                if isinstance(gen.target, ast.Name):
                    self.env[gen.target.id] = val
                else:
                    raise ValueError("Unsupported target in comprehension")

                elt_val = self.visit(node.elt)
                results.append(elt_val)

        self.env = saved_env
        return results



def safe_eval(expr: str, env: dict, registry: dict):
    """Safely evaluate expression string with env + registry"""
    tree = ast.parse(expr, mode="eval")
    evaluator = SafeEval(env, registry)
    result = evaluator.visit(tree.body)   
    if result is None:
        raise ValueError(f"Expression '{expr}' evaluated to None")
    return result


