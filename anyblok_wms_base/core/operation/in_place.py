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
    OperationInputsError,
    )

Mixin = Declarations.Mixin
Model = Declarations.Model


@Declarations.register(Mixin)
class WmsInPlaceOperation:
    """Mixin for Operations that happen in place.

    For these Operations, all inputs are in the same location, and
    the locations of their outcomes is the one of the inputs.
    """

    @classmethod
    def check_create_conditions(cls, state, dt_execution, inputs=None,
                                **fields):
        """Check that ``inputs`` locations are all the same."""
        super(WmsInPlaceOperation, cls).check_create_conditions(
            state, dt_execution, inputs=inputs, **fields)
        # In particular, we're now guaranteed that inputs is not None
        cls.unique_inputs_location(inputs)

    @classmethod
    def unique_inputs_location(cls, inputs):
        """Return the unique location of the given Avatars.

        :param inputs: the Avatars to check and extract from.
        :returns: the unique location
        :raises: OperationInputsError in case location is not unique among
                 ``inputs``
        """
        inputs_iter = iter(inputs)
        loc = next(inputs_iter).location
        if any(inp.location != loc for inp in inputs_iter):
            raise OperationInputsError(
                cls,
                "Inputs {inputs} are in different Locations: {locations!r}",
                inputs=inputs,
                # in the passing case, building a set would have been
                # useless overhead
                locations=set(inp.location for inp in inputs))
        return loc

    def input_location_altered(self):
        """An in place Operation must propagate change of locations.

        This checks that the inputs locations are still all the same,
        updates the location of the outcomes and notifies the followers.

        :raises: OperationInputsError if the inputs locations now differ
        """
        outcomes = self.outcomes
        new_loc = self.unique_inputs_location(self.inputs)
        for av in outcomes:
            av.location = new_loc
        for follower in self.followers:
            follower.input_location_altered()
