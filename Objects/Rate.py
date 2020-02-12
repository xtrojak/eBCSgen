import numpy as np
import sympy
from lark import Transformer, Tree

from TS.State import State


class Rate:
    def __init__(self, expression):
        self.expression = expression

    def __eq__(self, other):
        return self.expression == other.expression

    def __repr__(self):
        return str(self)

    def __str__(self):
        return self.expression if type(self.expression) == str else "".join(to_string(self.expression))

    def vectorize(self, ordering: tuple) -> list:
        """
        Converts all occurrences of Complexes (resp. sub trees named agent)
        with its vector representation. These are directly replaced within
        the tree expression.

        :param ordering: given tuple of Complexes
        :return: list of transformed States (just for testing)
        """
        vec = Vectorizer(ordering)
        self.expression = vec.transform(self.expression)
        return vec.visited

    def evaluate(self, state: State):
        evaluater = Evaluater(state)
        result = evaluater.transform(self.expression)
        return sympy.sympify("".join(to_string(result)))


class Vectorizer(Transformer):
    def __init__(self, ordering):
        super(Transformer, self).__init__()
        self.ordering = ordering
        self.visited = []

    def agent(self, complex):
        complex = complex[0]
        result = np.zeros(len(self.ordering))
        for i in range(len(self.ordering)):
            if complex.compatible(self.ordering[i]):
                result[i] = 1

        result = State(result)
        self.visited.append(result)
        return Tree("agent", [result])

    def rate_agent(self, matches):
        return matches[1]


class Evaluater(Transformer):
    def __init__(self, state):
        super(Transformer, self).__init__()
        self.state = state

    def agent(self, state):
        return sum(self.state * state[0])


def to_string(tree):
    if type(tree) == Tree:
        return sum(list(map(to_string, tree.children)), [])
    else:
        return [str(tree)]
