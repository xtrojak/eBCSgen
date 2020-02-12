import unittest
import numpy as np
import sympy

from Objects.Atomic import AtomicAgent
from Objects.Complex import Complex
from Objects.Rate import Rate
from Objects.Structure import StructureAgent
from Parsing.ParseModel import Parser
from TS.State import State


class TestRate(unittest.TestCase):
    def setUp(self):
        # agents

        self.a1 = AtomicAgent("T", "i")
        self.a2 = AtomicAgent("S", "i")
        self.a3 = AtomicAgent("T", "a")
        self.a4 = AtomicAgent("S", "a")

        self.s1 = StructureAgent("X", {self.a4})
        self.s2 = StructureAgent("X", {self.a2})
        self.s3 = StructureAgent("K", {self.a3})
        self.s4 = StructureAgent("K", {self.a1})
        self.s5 = StructureAgent("X", set())
        self.s6 = StructureAgent("K", set())

        self.c1 = Complex([self.s6], "cyt")  # K()::cyt
        self.c2 = Complex([self.s3], "cyt")  # K(T{a})::cyt
        self.c3 = Complex([self.s4], "cyt")  # K(T{i})::cyt
        self.c4 = Complex([self.s4, self.s1], "cyt")  # K(T{i}).X(S{a})::cyt
        self.c5 = Complex([self.s4, self.s2], "cyt")  # K(T{i}).X(S{i})::cyt
        self.c6 = Complex([self.s3, self.s1], "cyt")  # K(T{a}).X(S{a})::cyt
        self.c7 = Complex([self.s3, self.s2], "cyt")  # K(T{a}).X(S{i})::cyt

        # rates

        self.parser = Parser("rate")
        rate_expr = "3*[K()::cyt]/2*v_1"

        self.rate_1 = Rate(self.parser.parse(rate_expr))

        rate_expr = "3*[K(T{i}).X()::cyt] + [K()::cyt]"

        self.rate_2 = Rate(self.parser.parse(rate_expr))

        # states

        self.state_1 = State(np.array([2, 3]))
        self.state_2 = State(np.array([2, 0, 3, 1, 6, 2]))

    def test_to_str(self):
        self.assertEqual(str(self.rate_1), "3*[K()::cyt]/2*v_1")

    def test_eq(self):
        self.assertEqual(self.rate_2, self.rate_2)
        self.assertNotEqual(self.rate_1, self.rate_2)

    def test_vectorize(self):
        ordering = (self.c2, self.c3)
        self.assertEqual(self.rate_1.vectorize(ordering), [State(np.array([1, 1]))])
        ordering = (self.c2, self.c3, self.c4, self.c5, self.c6, self.c7)
        self.assertEqual(self.rate_2.vectorize(ordering), [State(np.array([0, 0, 1, 1, 0, 0])),
                                                           State(np.array([1, 1, 0, 0, 0, 0]))])

    def test_evaluate(self):
        ordering = (self.c2, self.c3)
        self.rate_1.vectorize(ordering)
        self.assertEqual(self.rate_1.evaluate(self.state_1), sympy.sympify("3*5.0/2*v_1"))

        ordering = (self.c2, self.c3, self.c4, self.c5, self.c6, self.c7)
        self.rate_2.vectorize(ordering)
        self.assertEqual(self.rate_2.evaluate(self.state_2), sympy.sympify("3*4.0 + 2"))
