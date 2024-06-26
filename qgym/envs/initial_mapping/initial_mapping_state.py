"""This module contains the :class:`~qgym.envs.initial_mapping.InitialMappingState`
class.

This :class:`~qgym.envs.InitialMapping` represents the :class:`~qgym.templates.State` of
the :class:`~qgym.envs.InitialMapping` environment.

Usage:
    >>> from qgym.envs.initial_mapping.initial_mapping_state import InitialMappingState
    >>> from qgym.envs.initial_mapping.graph_generation import BasicGraphGenerator
    >>> import networkx as nx
    >>> connection_graph = nx.grid_graph((3,3))
    >>> graph_generator = BasicGraphGenerator(9, 0.5)
    >>> state = InitialMappingState(connection_graph, graph_generator)

"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, cast

import networkx as nx
import numpy as np
from numpy.typing import NDArray

from qgym import spaces
from qgym.generators.graph import GraphGenerator
from qgym.templates.state import State


class InitialMappingState(State[Dict[str, NDArray[np.int_]], NDArray[np.int_]]):
    """The :class:`~qgym.envs.initial_mapping.InitialMappingState` class."""

    __slots__ = (
        "steps_done",
        "graphs",
        "mapping",
        "mapping_dict",
        "mapped_qubits",
    )

    def __init__(
        self, connection_graph: nx.Graph, graph_generator: GraphGenerator
    ) -> None:
        # pylint: disable=line-too-long
        """Init of the :class:`~qgym.envs.initial_mapping.InitialMappingState` class.

        Args:
            connection_graph: `networkx Graph <https://networkx.org/documentation/stable/reference/classes/graph.html>`_
                representation of the QPU topology. Each node represents a physical
                qubit and each edge represents a connection in the QPU topology.
            graph_generator: Graph generator for generating interaction graphs. This
                generator is used to generate a new interaction graph when
                :func:`InitialMappingState.reset` is called without an interaction
                graph.
        """
        # pylint: enable=line-too-long

        # Create a random connection graph with `n_nodes` and with edges existing with
        # probability `interaction_graph_edge_probability` (nodes without connections
        # can be seen as 'null' nodes)
        interaction_graph = next(graph_generator)

        self.steps_done: int = 0
        """Number of steps done since the last reset."""

        connection = {
            "graph": deepcopy(connection_graph),
            "matrix": nx.to_numpy_array(connection_graph, dtype=np.float_),
        }

        self.graphs = {
            "connection": connection,
            "interaction": {
                "graph": deepcopy(interaction_graph),
                "matrix": nx.to_numpy_array(interaction_graph, dtype=np.int8).flatten(),
                "generator": graph_generator,
            },
        }
        """Dictionary containing the graph and matrix representations of the both the
        interaction graph and connection graph.
        """
        self.mapping = np.full(self.n_nodes, self.n_nodes, dtype=np.int_)
        """Array of which the index represents a physical qubit, and the value a virtual
        qubit. A value of ``n_nodes + 1`` represents the case when nothing is mapped to
        the physical qubit yet.
        """
        self.mapping_dict: dict[int, int] = {}
        """Dictionary that maps logical qubits (keys) to physical qubits (values)."""
        self.mapped_qubits: dict[str, set[int]] = {"physical": set(), "logical": set()}
        """Dictionary with two sets containing mapped physical and logical qubits."""

    def create_observation_space(self) -> spaces.Dict:
        """Create the corresponding observation space.

        Returns:
            Observation space in the form of a :class:`~qgym.spaces.Dict` space
            containing the following values if the connection graph has no fidelity
            information:

            * :class:`~qgym.spaces.MultiDiscrete` space representing the mapping.
            * :class:`~qgym.spaces.MultiBinary` representing the interaction matrix.
        """
        mapping_space = spaces.MultiDiscrete(
            nvec=[self.n_nodes + 1] * self.n_nodes, rng=self.rng
        )
        interaction_matrix_space = spaces.MultiBinary(self.n_nodes**2, rng=self.rng)

        return spaces.Dict(
            rng=self.rng,
            mapping=mapping_space,
            interaction_matrix=interaction_matrix_space,
        )

    def reset(
        self,
        *,
        seed: int | None = None,
        interaction_graph: nx.Graph | None = None,
        **_kwargs: Any,
    ) -> InitialMappingState:
        """Reset the state and set a new interaction graph.

        To be used after an episode is finished.

        Args:
            seed: Seed for the random number generator, should only be provided
                (optionally) on the first reset call i.e., before any learning is done.
            interaction_graph: Interaction graph to be used for the next iteration, if
            ``None`` a random interaction graph will be created.
            _kwargs: Additional options to configure the reset.

        Returns:
            (self) New initial state.
        """
        if seed is not None:
            self.seed(seed)

        # Reset the state
        if interaction_graph is None:
            self.graphs["interaction"]["graph"] = next(
                self.graphs["interaction"]["generator"]
            )
        else:
            self.graphs["interaction"]["graph"] = deepcopy(interaction_graph)

        self.graphs["interaction"]["matrix"] = nx.to_numpy_array(
            self.graphs["interaction"]["graph"], dtype=np.int8
        ).flatten()

        self.steps_done = 0
        self.mapping = np.full(self.n_nodes, self.n_nodes)
        self.mapping_dict = {}
        self.mapped_qubits = {"physical": set(), "logical": set()}

        return self

    def update_state(self, action: NDArray[np.int_]) -> InitialMappingState:
        """Update the state (in place) of this environment using the given action.

        Args:
            action: Mapping action to be executed.

        Returns:
            Self.
        """
        # Increase the step number
        self.steps_done += 1

        # update state based on the given action
        physical_qubit, logical_qubit = action

        if (
            physical_qubit in self.mapped_qubits["physical"]
            or logical_qubit in self.mapped_qubits["logical"]
        ):
            return self

        self.mapping[physical_qubit] = logical_qubit
        self.mapping_dict[logical_qubit] = physical_qubit
        self.mapped_qubits["physical"].add(physical_qubit)
        self.mapped_qubits["logical"].add(logical_qubit)
        return self

    def obtain_observation(self) -> dict[str, NDArray[np.int_]]:
        """Obtain an observation based on the current state.

        Returns:
            Observation based on the current state.
        """
        return {
            "mapping": self.mapping,
            "interaction_matrix": self.graphs["interaction"]["matrix"],
        }

    def is_done(self) -> bool:
        """Determine if the state is done or not.

        Returns:
            Boolean value stating whether we are in a final state.
        """
        return bool(len(self.mapping_dict) == self.n_nodes)

    def is_truncated(self) -> bool:
        """Determine if the episode should be truncated or not.

        Returns:
            Boolean value stating whether the episode should be truncated. The episode
            is truncated if the number of steps in the current episode is more than 10
            times the number of nodes in the connection graph.
        """
        return bool(self.steps_done > self.n_nodes * 10)

    def obtain_info(self) -> dict[str, Any]:
        """Obtain additional information.

        Returns:
            Optional debugging info for the current state.
        """
        return {
            "Steps done": self.steps_done,
            "Mapping": self.mapping,
            "Mapping Dictionary": self.mapping_dict,
            "Mapped Qubits": self.mapped_qubits,
        }

    @property
    def n_nodes(self) -> int:
        """The number of physical qubits."""
        return cast(int, self.graphs["connection"]["graph"].number_of_nodes())
