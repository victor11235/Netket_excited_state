# Copyright 2021 The NetKet Authors - All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import jax
import jax.numpy as jnp
import netket

from textwrap import dedent

from netket.utils.types import PyTree
from netket.operator import AbstractOperator
from netket.stats import Stats
from netket.vqs import MCState
from netket.optimizer import (
    identity_preconditioner,
    PreconditionerT,
)
from netket.utils import warn_deprecation


from netket.driver.vmc_common import info
from netket.driver.abstract_variational_driver import AbstractVariationalDriver

import expect_grad_ex


class VMC_ex(AbstractVariationalDriver):
    """
    Energy minimization using Variational Monte Carlo (VMC).
    """

    # TODO docstring
    def __init__(
        self,
        hamiltonian: AbstractOperator,
        optimizer,
        *args,
        variational_state=None,
        preconditioner: PreconditionerT = None,
        sr: PreconditionerT = None,
        sr_restart: bool = None,
        state_list,
        shift_list,
        **kwargs,

    ):
        """
        Initializes the driver class.

        Args:
            hamiltonian: The Hamiltonian of the system.
            optimizer: Determines how optimization steps are performed given the
                bare energy gradient.
            preconditioner: Determines which preconditioner to use for the loss gradient.
                This must be a tuple of `(object, solver)` as documented in the section
                `preconditioners` in the documentation. The standard preconditioner
                included with NetKet is Stochastic Reconfiguration. By default, no
                preconditioner is used and the bare gradient is passed to the optimizer.
            state_list: a set of previously determined states in a list
            shift_list: contains the energy shifts for each previously determined state
        """
        if variational_state is None:
            variational_state = MCState(*args, **kwargs)

        if variational_state.hilbert != hamiltonian.hilbert:
            raise TypeError(
                dedent(
                    f"""the variational_state has hilbert space {variational_state.hilbert}
                    (this is normally defined by the hilbert space in the sampler), but
                    the hamiltonian has hilbert space {hamiltonian.hilbert}.
                    The two should match.
                    """
                )
            )

        if sr is not None:
            if preconditioner is not None:
                raise ValueError(
                    "sr is deprecated in favour of preconditioner kwarg. You should not pass both"
                )
            else:
                preconditioner = sr
                warn_deprecation(
                    (
                        "The `sr` keyword argument is deprecated in favour of `preconditioner`."
                        "Please update your code to `VMC(.., precondioner=your_sr)`"
                    )
                )
        if sr_restart is not None:
            if preconditioner is None:
                raise ValueError(
                    "sr_restart only makes sense if you have a preconditioner/SR."
                )
            else:
                preconditioner.solver_restart = sr_restart
                warn_deprecation(
                    (
                        "The `sr_restart` keyword argument is deprecated in favour of specifiying "
                        "`solver_restart` in the constructor of the SR object."
                        "Please update your code to `VMC(.., preconditioner=nk.optimizer.SR(..., solver_restart=True/False))`"
                    )
                )

        # move as kwarg once deprecations are removed
        if preconditioner is None:
            preconditioner = identity_preconditioner

        super().__init__(variational_state, optimizer, minimized_quantity_name="Energy")

        self._ham = hamiltonian.collect()  # type: AbstractOperator

        self.preconditioner = preconditioner

        self._dp = None  # type: PyTree
        self._S = None
        self._sr_info = None
        self._state_list = state_list
        self._shift_list = shift_list

    def _forward_and_backward(self):
        """
        Performs a number of VMC optimization steps.

        Args:
            n_steps (int): Number of steps to perform.
        """

        self.state.reset()

        #we also need to reset MCMC samples for each state in the list
        for state_i in self._state_list:
            state_i.reset()

        # Compute the local energy estimator and average Energy
        self._loss_stats, self._loss_grad = expect_grad_ex.expect_and_grad_ex(
            self.state,
            self._ham, 
            True,                             
            self.state.mutable, 
            self._state_list, 
            self._shift_list,
        )
       
        

        # if it's the identity it does
        # self._dp = self._loss_grad
        self._dp = self.preconditioner(self.state, self._loss_grad)

        # If parameters are real, then take only real part of the gradient (if it's complex)
        self._dp = jax.tree_map(
            lambda x, target: (x if jnp.iscomplexobj(target) else x.real),
            self._dp,
            self.state.parameters,
        )

        return self._dp

    @property
    def energy(self) -> Stats:
        """
        Return MCMC statistics for the expectation value of observables in the
        current state of the driver.
        """
        return self._loss_stats

    def __repr__(self):
        return (
            "Vmc("
            + f"\n  step_count = {self.step_count},"
            + f"\n  state = {self.state})"
        )

    def info(self, depth=0):
        lines = [
            "{}: {}".format(name, info(obj, depth=depth + 1))
            for name, obj in [
                ("Hamiltonian    ", self._ham),
                ("Optimizer      ", self._optimizer),
                ("Preconditioner ", self.preconditioner),
                ("State          ", self.state),
            ]
        ]
        return "\n{}".format(" " * 3 * (depth + 1)).join([str(self)] + lines)