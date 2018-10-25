# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
"""Mixins for Operations that take exactly on PhysObj record as input.
"""

from anyblok import Declarations

from anyblok_wms_base.exceptions import (
    OperationError,
)

Mixin = Declarations.Mixin
Model = Declarations.Model
Wms = Model.Wms


@Declarations.register(Mixin)
class WmsSingleInputOperation:
    """Mixin for Operations that apply to a single record of PhysObj.

    This is synctactical sugar, allowing to work with such Operations as if
    Operations weren't meant in general for multiple inputs.
    """

    inputs_number = 1
    """Tell the base class that, indeed, we expect a single input."""

    @property
    def input(self):
        """Convenience attribute to refer to the single element of ``inputs``.
        """
        inps = self.inputs
        if not inps:  # can happen as an intermediate deletion step
            return '<unlinked>'
        return inps[0]

    @classmethod
    def create(cls, input=None, inputs=None, **kwargs):
        """Accept the alternative ``input`` arg and call back the base class.

        This override is for convenience in a case of a single input.
        """
        if input is not None and inputs is not None:
            # not an OperationInputsError, because it's not about the
            # contents of the inputs (one could say they aren't really known
            raise OperationError(
                cls,
                "You must choose between the 'input' and the 'inputs' "
                "kwargs (got input={input}, inputs={inputs}",
                input=input, inputs=inputs)
        if input is not None:
            inputs = (input, )
        return super(WmsSingleInputOperation, cls).create(
            inputs=inputs, **kwargs)

    def specific_repr(self):
        return "input={self.input!r}".format(self=self)

    def refine_with_leading_move(self, stopover):
        """Split the current Operation in two, the first one being a Move

        :param stopover: this is the location of the intermediate Avatar
                         that's been introduced (destination of the Move).
        :return: the new Move

        This doesn't change anything for the Operations that the current
        Operation follows, and in fact, it is guaranteed that their outcomes
        are untouched by this method.

        This may recurse for consequences of the fact that the location of
        ``self.input`` changes in the process (and in fact it's a new Avatar),
        but it is expected that this should be used mostly for Operations for
        which the location of the inputs don't matter, such as Move or
        Departure.

        Example use case: Rather than planning a Move from stock to a shipping
        area, followed by a Departure, one may wish to just plan a Departure
        directly from the stock location, and later on, refine
        this as Move, then Departure.
        This is especially useful if the shipping area can't be
        determined at the time of the original planning, or simply to follow
        the general principle of sober planning.
        """
        self.check_alterable()
        move = self.registry.Wms.Operation.Move.create(
            input=self.input,
            destination=stopover,
            dt_execution=self.dt_execution,
            state='planned')
        self.link_inputs(move.outcomes, clear=True)
        self.input_location_altered()
        return move
