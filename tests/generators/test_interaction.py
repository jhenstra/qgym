"""This module contains tests for the iteration generation module."""

from collections.abc import Iterator

import networkx as nx
import numpy as np
import pytest

from qgym.generators.interaction import (
    BasicInteractionGenerator,
    InteractionGenerator,
    NullInteractionGenerator,
)


def test_abc() -> None:
    with pytest.raises(TypeError):
        InteractionGenerator()  # type: ignore[abstract]


class TestNullInteractionGenerator:

    @pytest.fixture(name="generator")
    def null_interaction_generator_fixture(self) -> NullInteractionGenerator:
        return NullInteractionGenerator()

    def test_set_state_attributes(self, generator: NullInteractionGenerator) -> None:
        assert len(vars(generator)) == 1
        generator.set_state_attributes()
        assert len(vars(generator)) == 1

    def test_infinite(self, generator: NullInteractionGenerator) -> None:
        assert not generator.finite

    def test_inheritance(self, generator: NullInteractionGenerator) -> None:
        assert isinstance(generator, InteractionGenerator)
        assert isinstance(generator, Iterator)

    def test_next(self, generator: NullInteractionGenerator) -> None:
        circuit = next(generator)
        assert isinstance(circuit, np.ndarray)
        assert circuit.dtype == np.int_
        assert len(circuit) == 0

    def test_iter(self, generator: NullInteractionGenerator) -> None:
        for i, circuit in enumerate(generator):
            assert isinstance(circuit, np.ndarray)
            assert circuit.dtype == np.int_
            assert len(circuit) == 0

            if i > 100:
                break


class TestBasicGraphGenerator:

    @pytest.fixture(name="simple_generator")
    def null_interaction_generator_fixture(self) -> BasicInteractionGenerator:
        generator = BasicInteractionGenerator()
        generator.set_state_attributes(connection_graph=nx.empty_graph(5))
        return generator

    def test_set_state_attributes(self) -> None:
        generator = BasicInteractionGenerator()
        assert not hasattr(generator, "n_qubits")

        generator.set_state_attributes(connection_graph=nx.empty_graph(5))
        assert generator.n_qubits == 5

    def test_infinite(self, simple_generator: BasicInteractionGenerator) -> None:
        assert not simple_generator.finite

    def test_inheritance(self, simple_generator: BasicInteractionGenerator) -> None:
        assert isinstance(simple_generator, InteractionGenerator)
        assert isinstance(simple_generator, Iterator)

    def test_next(self, simple_generator: BasicInteractionGenerator) -> None:
        circuit = next(simple_generator)
        assert isinstance(circuit, np.ndarray)
        assert circuit.dtype == np.int_
        assert circuit.ndim == 2
        assert circuit.shape[1] == 2
        assert len(circuit) <= simple_generator.max_length

    def test_iter(self, simple_generator: BasicInteractionGenerator) -> None:
        for i, circuit in enumerate(simple_generator):
            assert isinstance(circuit, np.ndarray)
            assert circuit.dtype == np.int_
            assert circuit.ndim == 2
            assert circuit.shape[1] == 2
            assert len(circuit) <= simple_generator.max_length

            if i > 100:
                break

    def test_seed(self) -> None:
        generator1 = BasicInteractionGenerator(seed=1)
        generator2 = BasicInteractionGenerator(seed=1)
        generator3 = BasicInteractionGenerator(seed=3)

        for generator in [generator1, generator2, generator3]:
            generator.set_state_attributes(connection_graph=nx.empty_graph(10))

        for _ in range(10):
            circuit1 = next(generator1)
            circuit2 = next(generator2)
            circuit3 = next(generator3)

            np.testing.assert_array_equal(circuit1, circuit2)
            if len(circuit1) == len(circuit3):
                assert np.any(circuit1 != circuit3)
