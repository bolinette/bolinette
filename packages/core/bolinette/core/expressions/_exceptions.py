from bolinette.core import expressions
from bolinette.core.exceptions import BolinetteError, ParameterError


class ExpressionError(BolinetteError, ParameterError):
    def __init__(self, expr: "expressions.ExpressionNode", message: str) -> None:
        ParameterError.__init__(self, expr="Expression {}")
        BolinetteError.__init__(self, self._format_params(message, expr=expr))


class MaxDepthExpressionError(ExpressionError):
    def __init__(self, expr: "expressions.ExpressionNode") -> None:
        super().__init__(expr, "Expression exceeds allowed depth")


class AttributeChainError(ExpressionError):
    def __init__(self, expr: "expressions.ExpressionNode") -> None:
        super().__init__(expr, "Expression is excepted to be a chain of attribute access")
