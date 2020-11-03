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
from anyblok_wms_base.constants import EMPTY_TIMESPAN

Mixin = Declarations.Mixin
Model = Declarations.Model


@Declarations.register(Mixin)
class WmsSingleOutcomeOperation:
    """Mixin for Operations that produce a single outcome.

    This is synctactical sugar, allowing to work with such Operations as if
    Operations couldn't in general produce several outcomes.
    """

    @property
    def outcome(self):
        """Convenience attribute to return the unique outcome.
        """
        Avatar = self.registry.Wms.PhysObj.Avatar
        return Avatar.query().filter_by(outcome_of=self).one()

    def refine_with_trailing_move(self, stopover):
        """Split the current Operation in two, the last one being a Move

        This is for Operations that are responsible for the location of
        their outcome (see the :attr:`destination_field
        <anyblok_wms_base.core.operation.base.Operation.destination_field>`
        class attribute)

        :param stopover: this is the location of the intermediate Avatar
                         that's been introduced (starting point of the Move).
        :param dt_execution: TODO not supported yet
        :returns: the new Move instance

        This doesn't change anything for the followers of the current
        Operation, and in fact, it is guaranteed that their inputs are
        untouched by this method.

        Example use case: Rather than planning an Arrival followed by a Move to
        stock location, One may wish to just plan an Arrival into some
        the final stock destination, and later on, refine
        this as an Arrival in a landing area, followed by a Move to the stock
        destination. This is especially useful if the landing area can't be
        determined at the time of the original planning, or simply to follow
        the general principle of sober planning.

        """
        self.check_alterable()
        field = self.destination_field
        if field is None:
            raise OperationError(
                self,
                "Can't refine {op} with a trailing move, because it's "
                "not responsible for the location of its outcomes",
                op=self)
        setattr(self, field, stopover)

        final_outcome = self.outcome
        stopover_outcome = self.registry.Wms.PhysObj.Avatar.insert(
            location=stopover,
            outcome_of=self,
            state='future',
            timespan=EMPTY_TIMESPAN,
            obj=final_outcome.obj)
        return self.registry.Wms.Operation.Move.plan_for_outcomes(
            (stopover_outcome, ), (final_outcome, ),
            dt_execution=self.dt_execution)
