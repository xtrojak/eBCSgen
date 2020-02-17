import collections
from copy import deepcopy
from lark import Lark, Transformer, Tree
from lark import UnexpectedCharacters, UnexpectedToken

from Core.Atomic import AtomicAgent
from Core.Complex import Complex
from Core.Model import Model
from Core.Rate import Rate
from Core.Rule import Rule
from Core.Structure import StructureAgent


class SideHelper:
    def __init__(self):
        self.seq = []
        self.comp = []
        self.complexes = []
        self.counter = 0

    def __str__(self):
        return " | ".join([str(self.seq), str(self.comp), str(self.complexes), str(self.counter)])

    def __repr__(self):
        return str(self)


GRAMMAR = r"""
    model: rules inits definitions

    rules: "#! rules" rule+
    inits: "#! inits" init+
    definitions: "#! definitions" definition+

    init: const? rate_complex
    definition: def_param "=" number
    rule: side "=>" side ("@" rate)?

    side: (const? complex "+")* (const? complex)?
    complex: sequence "::" compartment
    sequence: (agent ".")* agent
    agent: atomic | structure
    structure: s_name "()" | s_name "(" composition ")"
    composition: (atomic ",")* atomic?
    atomic : a_name "{" state "}" | a_name

    !rate : fun "/" fun | fun
    !fun: const | param | rate_agent | fun "+" fun | fun "*" fun | fun "^" const | "(" fun ")"

    !rate_agent: "[" rate_complex "]"

    rate_complex: sequence "::" compartment

    !state: (DIGIT|LETTER|"+"|"-"|"*"|"_")+

    a_name: CNAME
    s_name: CNAME
    compartment: CNAME
    param: CNAME
    def_param : CNAME
    number: DECIMAL

    const: DIGIT

    %import common.LETTER
    %import common.DIGIT
    %import common.CNAME
    %import common.DECIMAL
    %import common.WS
    %ignore WS
"""


class TreeToObjects(Transformer):
    def state(self, matches):
        return "".join(map(str, matches))

    def atomic(self, matches):
        name, state = str(matches[0].children[0]), matches[1]
        return AtomicAgent(name, state)

    def structure(self, matches):
        name = str(matches[0].children[0])
        if len(matches) > 1:
            composition = set(matches[1].children)
            return StructureAgent(name, composition)
        else:
            return StructureAgent(name, set())

    def rate_complex(self, matches):
        sequence = []
        for item in matches[0].children:
            sequence.append(item.children[0])
        compartment = matches[1]
        return Tree("agent", [Complex(collections.Counter(sequence), compartment)])

    def compartment(self, matches):
        return str(matches[0])

    def const(self, matches):
        return int(matches[0])

    def def_param(self, matches):
        return str(matches[0])

    def number(self, matches):
        return float(matches[0])

    def side(self, matches):
        helper = SideHelper()
        stochio = 1
        for item in matches:
            if type(item) == int:
                stochio = item
            else:
                agents = item.children[0]
                compartment = item.children[1]
                for i in range(stochio):
                    start = helper.counter
                    for agent in agents.children:
                        helper.seq.append(deepcopy(agent.children[0]))
                        helper.comp.append(compartment)
                        helper.counter += 1
                    helper.complexes.append((start, helper.counter - 1))
        return helper

    def rule(self, matches):
        if len(matches) > 2:
            lhs, rhs, rate = matches
        else:
            lhs, rhs = matches
            rate = None
        agents = tuple(lhs.seq + rhs.seq)
        mid = lhs.counter
        compartments = lhs.comp + rhs.comp
        complexes = lhs.complexes + list(
            map(lambda item: (item[0] + lhs.counter, item[1] + lhs.counter), rhs.complexes))
        pairs = [(i, i + lhs.counter) for i in range(min(lhs.counter, rhs.counter))]
        if lhs.counter > rhs.counter:
            pairs += [(i, None) for i in range(rhs.counter, lhs.counter)]
        elif lhs.counter < rhs.counter:
            pairs += [(None, i + lhs.counter) for i in range(lhs.counter, rhs.counter)]

        return Rule(agents, mid, compartments, complexes, pairs, Rate(rate) if rate else None)

    def rules(self, matches):
        return matches

    def definitions(self, matches):
        result = dict()
        for definition in matches:
            pair = definition.children
            result[pair[0]] = pair[1]
        return result

    def init(self, matches):
        return matches

    def inits(self, matches):
        result = collections.Counter()
        for init in matches:
            if len(init) > 1:
                result[init[1].children[0]] = init[0]
            else:
                result[init[0].children[0]] = 1
        return result

    def model(self, matches):
        return Model(set(matches[0]), matches[1], matches[2], None)


class Result:
    def __init__(self, success, data):
        self.success = success
        self.data = data


class Parser:
    def __init__(self, start):
        grammar = "start: " + start + GRAMMAR
        self.parser = Lark(grammar, parser='lalr',
                           propagate_positions=False,
                           maybe_placeholders=False,
                           transformer=TreeToObjects()
                           )

    def parse(self, expression):
        try:
            return Result(True, self.parser.parse(expression).children[0])
        except UnexpectedCharacters as u:
            print("Wrong '", expression[u.pos_in_stream], "'")
            print("Expected: ", u.allowed)
            print("At: ", u.line, u.column)
        except UnexpectedToken as u:
            print("Wrong '", u.token, "'")
            print("Expected: ", u.expected)
            print("At: ", u.line, u.column)
