# calculator.py

class Calculator:
    def __init__(self):
        # Define supported operators and their corresponding functions
        self.operators = {
            "+": lambda a, b: a + b,
            "-": lambda a, b: a - b,
            "*": lambda a, b: a * b,
            "/": lambda a, b: a / b,
        }
        # Define operator precedence (higher number = higher precedence)
        # Multiplication and division have higher precedence than addition and subtraction.
        self.precedence = {
            "+": 1,
            "-": 1,
            "*": 2,
            "/": 2,
        }

    def evaluate(self, expression):
        """Evaluate a space-separated infix arithmetic expression.

        Returns the numeric result, or None for an empty/whitespace string.
        Raises ValueError for invalid tokens or malformed expressions.
        """
        if not expression or expression.isspace():
            return None
        tokens = expression.strip().split()
        return self._evaluate_infix(tokens)

    def _evaluate_infix(self, tokens):
        """Evaluate tokens using the Shunting-Yard algorithm.

        values holds the operand stack, operators holds the operator stack.
        """
        values = []
        operators = []

        for token in tokens:
            if token in self.operators:
                # While there is an operator on the stack with greater or equal precedence,
                # apply it before pushing the current operator.
                while (
                    operators
                    and operators[-1] in self.operators
                    and self.precedence[operators[-1]] >= self.precedence[token]
                ):
                    self._apply_operator(operators, values)
                operators.append(token)
            else:
                # Token should be a number.
                try:
                    values.append(float(token))
                except ValueError:
                    raise ValueError(f"invalid token: {token}")

        # Apply any remaining operators.
        while operators:
            self._apply_operator(operators, values)

        if len(values) != 1:
            raise ValueError("invalid expression")

        return values[0]

    def _apply_operator(self, operators, values):
        """Pop an operator and two operands, apply the operation, and push the result.
        """
        if not operators:
            return

        operator = operators.pop()
        if len(values) < 2:
            raise ValueError(f"not enough operands for operator {operator}")

        b = values.pop()
        a = values.pop()
        values.append(self.operators[operator](a, b))
