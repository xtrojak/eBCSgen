import unittest

import Parsing.ParsePCTLformula
from Parsing.ParseBCSL import Parser


class TestFormalMethods(unittest.TestCase):
    def setUp(self):
        self.parser = Parsing.ParsePCTLformula.PCTLparser()
        self.model_parser = Parser("model")
        self.model = """
            #! rules
            Y{i}::rep => Y{a}::rep @ p*[Y{i}::rep]
            Y{i}::rep => Y{-}::rep @ (1-p)*[Y{i}::rep]
            X()::rep + Y{a}::rep => X().Y{a}::rep @ q*[X()::rep]*[Y{a}::rep]
            X(K{i}).Y{_}::rep => X(K{p}).Y{_}::rep @ p*[X(K{i}).Y{_}::rep] // also here

            #! inits
            2 X(K{i})::rep
            1 Y{i}::rep

            #! definitions
            p = 0.3
        """

        self.tumor = """
            #! rules
            T(P{i})::x => T(P{m})::x @ a1*[T(P{i})::x]
            T(P{m})::x => T(P{i})::x + T(P{i})::x @ a2*[T(P{m})::x]
            T(P{i})::x => @ d1*[T(P{i})::x]
            T(P{m})::x => @ d2*[T(P{m})::x]

            #! inits
            2 T(P{m})::x
            1 T(P{i})::x

            #! definitions
            a1 = 1.2
            a2 = 2
            d1 = 0.8
            d2 = 0.5
        """

        self.tumor_parametric = """
            #! rules
            T(P{i})::x => T(P{m})::x @ a1*[T(P{i})::x]
            T(P{m})::x => T(P{i})::x + T(P{i})::x @ a2*[T(P{m})::x]
            T(P{i})::x => @ d1*[T(P{i})::x]
            T(P{m})::x => @ d2*[T(P{m})::x]

            #! inits
            2 T(P{m})::x
            1 T(P{i})::x

            #! definitions
            a1 = 1.2
            a2 = 2
            d1 = 0.8
        """

    def test_tumor_modelchecking(self):
        model_parsed = self.model_parser.parse(self.tumor).data
        result = model_parsed.PCTL_model_checking("P=? [F T(P{m})::x>2 & T(P{i})::x>=0 & T(P{i})::x<2]")
        self.assertTrue("Result" in str(result))

        result = model_parsed.PCTL_model_checking("P > 0.5 [F T(P{m})::x>2]")
        self.assertTrue("Result" in str(result))

    def test_tumor_modelchecking_wrong_formula(self):
        model_parsed = self.model_parser.parse(self.tumor).data
        result = model_parsed.PCTL_model_checking("P > 0.5 [F T(P{m}):x>2]")
        error_message = {'line': 1, 'column': 19, 'unexpected': ':', 'expected': {'DOUBLE_COLON', '.'}}
        self.assertEqual(result, error_message)

    def test_parameter_synthesis(self):
        model_parsed = self.model_parser.parse(self.tumor_parametric).data
        result = model_parsed.PCTL_synthesis("P=? [F T(P{m})::x>2]", None)
        self.assertTrue("Result" in str(result))

    def test_parametric_model(self):
        model_parsed = self.model_parser.parse(self.model).data

        result = model_parsed.PCTL_synthesis("P<=0.3 [F X().Y{_}::rep >= 1]", '0<=q<=1')
        self.assertTrue("Result (initial states)" in str(result))

        result = model_parsed.PCTL_synthesis("P=? [F X().Y{_}::rep >= 1]", None)
        self.assertTrue("Result (initial states)" in str(result))

    def test_synthesis_simple(self):
        model_str = """
        #! rules
        X()::rep => @ k1*[X()::rep]
        Z()::rep => X()::rep @ k2
        => Y()::rep @ 1/(1+([X()::rep])**4)

        #! inits
        2 X()::rep
        Y()::rep

        #! definitions
        k2 = 5
        """
        model = self.model_parser.parse(model_str).data
        formula = 'P <= 0.5[F X()::rep = 1]'
        region = '0<=k1<=1'
        output = model.PCTL_synthesis(formula, region)
        self.assertTrue("Region results" in str(output))

        formula = 'P=? [F X()::rep = 1]'
        output = model.PCTL_synthesis(formula, None)
        self.assertTrue("Result (initial states)" in str(output))

    def test_synthesis_advanced(self):
        model_str = """
        #! rules
        // commenting
        X(K{i})::rep => X(K{p})::rep @ k1*[X()::rep] // also here
        X(T{a})::rep => X(T{o})::rep @ k2*[Z()::rep]
        => Y(P{f})::rep @ 1/(1+([X()::rep])**4) // ** means power (^)

        #! inits
        2 X(K{c}, T{e}).X(K{c}, T{j})::rep
        Y(P{g}, N{l})::rep

        #! definitions
        k2 = 0.05 // also comment
        """
        model = self.model_parser.parse(model_str).data
        formula = 'P <= 0.5[F X()::rep = 1]'
        region = '0<=k1<=1'
        output = model.PCTL_synthesis(formula, region)
        self.assertTrue("Region results" in str(output))

        formula = 'P=? [F X()::rep = 1]'
        output = model.PCTL_synthesis(formula, None)
        self.assertTrue("Result (initial states)" in str(output))

    def test_model_checking_simple(self):
        model_str = """
        #! rules
        X()::rep => @ k1*[X()::rep]
        Z()::rep => X()::rep @ k2
        => Y()::rep @ 1/(1+([X()::rep])**4)

        #! inits
        2 X()::rep
        Y()::rep

        #! definitions
        k2 = 5
        k1 = 2
        """
        model = self.model_parser.parse(model_str).data
        formula = 'P <= 0.5[F X()::rep=1]'
        output = model.PCTL_model_checking(formula)
        self.assertTrue("Result (for initial states)" in str(output))

        formula = 'P=? [F X()::rep = 1]'
        output = model.PCTL_model_checking(formula)
        self.assertTrue("Result (for initial states)" in str(output))

    def test_model_checking_advanced(self):
        model_str = """
        #! rules
        // commenting
        X(K{i})::rep => X(K{p})::rep @ k1*[X()::rep] // also here
        X(T{a})::rep => X(T{o})::rep @ k2*[Z()::rep]
        => Y(P{f})::rep @ 1/(1+([X()::rep])**4) // ** means power (^)

        #! inits
        2 X(K{c}, T{e}).X(K{c}, T{j})::rep
        Y(P{g}, N{l})::rep

        #! definitions
        k2 = 0.05 // also comment
        k1 = 2
        """
        model = self.model_parser.parse(model_str).data
        formula = 'P >= 0.5[F X()::rep=1]'
        output = model.PCTL_model_checking(formula)
        self.assertTrue("Result (for initial states)" in str(output))

        formula = 'P=? [F X()::rep = 1]'
        output = model.PCTL_model_checking(formula)
        self.assertTrue("Result (for initial states)" in str(output))
