import threading
import pandas as pd

from TS.Edge import Edge


class TSworker(threading.Thread):
    def __init__(self, ts, model):
        super(TSworker, self).__init__()
        self.ts = ts  # resulting transition system
        self.model = model

        self.stop_request = threading.Event()
        self.work = threading.Event()  # to control whether the Worker is supposed to work

    def run(self):
        """
        Method takes a state from pool of states to be states and:
        1. iteratively applies all reactions on it
        2. checks whether newly created state (if any) was already states (present in self.ts.states_encoding)
           2.1 if not, it is added to self.states_to_process
        3. creates Edge from the source state to created one (since ts.edges is a set, we don't care about its presence)
        4. all outgoing Edges from the state are normalised to probability
        """
        while not self.stop_request.isSet():
            self.work.wait()
            try:
                state = self.ts.unprocessed.pop()
                self.ts.states.add(state)
                unique_states = dict()

                # special "hell" state
                if state.is_inf:
                    self.ts.edges.add(Edge(state, state, 1))
                else:
                    candidate_reactions = dict()
                    for reaction in self.model.vector_reactions:
                        new_state, rate = reaction.apply(state, self.model.bound)
                        if new_state and rate:
                            candidate_reactions[reaction] = (rate, new_state)

                    if self.model.regulation:
                        candidate_reactions = self.model.regulation.filter(state, candidate_reactions)

                    for reaction in candidate_reactions:
                        rate, new_state = candidate_reactions[reaction]
                        new_state = state.update_state(new_state, reaction.label)

                        if new_state not in self.ts.states:
                            self.ts.unprocessed.add(new_state)

                        # multiple arrows between two states are not allowed
                        if new_state in unique_states:
                            unique_states[new_state].add_rate(rate)
                        else:
                            edge = Edge(state, new_state, rate, reaction.label)
                            unique_states[new_state] = edge

                    edges = set(unique_states.values())

                    # normalise
                    factor = sum(list(map(lambda edge: edge.probability, edges)))
                    if edges:
                        for edge in edges:
                            edge.normalise(factor)
                            self.ts.edges.add(edge)
                    else:
                        # self loop to create correct DTMC
                        self.ts.edges.add(Edge(state, state, 1, 'ε'))

            except KeyError:
                self.work.clear()

    def join(self, timeout=None):
        self.work.set()
        self.stop_request.set()


class DirectTSworker(threading.Thread):
    def __init__(self, ts, model):
        super(DirectTSworker, self).__init__()
        self.ts = ts  # resulting transition system
        self.model = model

        self.stop_request = threading.Event()
        self.work = threading.Event()  # to control whether the Worker is supposed to work

    def run(self):
        """
        Method takes a state from pool of states to be states and:
        1. iteratively applies all rules on it
        2. checks whether newly created states (if any) were already states (present in self.ts.states_encoding)
           2.1 if not, it is added to self.states_to_process
        3. creates Edge from the source state to created ones (since ts.edges is a set, we don't care about its presence)
        4. all outgoing Edges from the state are normalised to probability
        """
        while not self.stop_request.isSet():
            self.work.wait()
            try:
                state = self.ts.unprocessed.pop()
                self.ts.states.add(state)
                unique_states = dict()

                # special "hell" state
                if state.is_inf:
                    self.ts.edges.add(Edge(state, state, 1))
                else:
                    candidate_rules = dict()
                    for rule in self.model.rules:
                        rate = rule.evaluate_rate(state, self.model.definitions)
                        match = rule.match(state, all=True)

                        try:
                            rate = rate if rate > 0 else None
                        except TypeError:
                            pass

                        # drop rules which cannot be actually used (0 rate or no matches)
                        if match is not None and rate is not None:
                            candidate_rules[rule] = (rate, match)

                    if self.model.regulation:
                        candidate_rules = self.model.regulation.filter(state, candidate_rules)

                    for rule in candidate_rules.keys():
                        for match in candidate_rules[rule][1]:
                            produced_agents = rule.replace(match)
                            match = rule.reconstruct_complexes_from_match(match)
                            new_state = state.update_state(match, produced_agents, rule.label)

                            new_state = new_state.validate_bound(self.ts.bound)

                            if new_state not in self.ts.states:
                                self.ts.unprocessed.add(new_state)
                                self.ts.unique_complexes.update(set(new_state.multiset))

                            # multiple arrows between two states are not allowed
                            if new_state in unique_states:
                                unique_states[new_state].add_rate(candidate_rules[rule][0])
                            else:
                                edge = Edge(state, new_state, candidate_rules[rule][0], rule.label)
                                unique_states[new_state] = edge

                    edges = set(unique_states.values())

                    # normalise
                    factor = sum(list(map(lambda edge: edge.probability, edges)))
                    if edges:
                        for edge in edges:
                            edge.normalise(factor)
                            self.ts.edges.add(edge)
                    else:
                        # self loop to create correct DTMC
                        self.ts.edges.add(Edge(state, state, 1, 'ε'))

            except KeyError:
                self.work.clear()

    def join(self, timeout=None):
        self.work.set()
        self.stop_request.set()
