# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.

from anyblok import Declarations
from anyblok.column import Integer
from anyblok.relationship import Many2One
from anyblok_wms_base.exceptions import (
    OperationError,
    OperationContainerExpected,
    )


register = Declarations.register
Mixin = Declarations.Mixin
Operation = Declarations.Model.Wms.Operation


@register(Operation)
class Move(Mixin.WmsSingleInputOperation,
           Mixin.WmsSingleOutcomeOperation,
           Operation):
    """A stock move
    """
    TYPE = 'wms_move'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))
    destination = Many2One(model='Model.Wms.PhysObj',
                           nullable=False)
    destination_field = 'destination'

    def specific_repr(self):
        return ("input={self.input!r}, "
                "destination={self.destination!r}").format(self=self)

    def after_insert(self):
        state, to_move, dt_exec = self.state, self.input, self.dt_execution
        orig_dt_until = to_move.dt_until
        if orig_dt_until is None:
            dt_until = None
        else:
            # it's not clear what it means for to_move.dt_until not to be None
            # in any case, dt_until should be at least dt_from
            dt_until = max(orig_dt_until, dt_exec)

        to_move.dt_until = dt_exec
        if state == 'done':
            to_move.state = 'past'
        self.registry.Wms.PhysObj.Avatar.insert(
            location=self.destination,
            outcome_of=self,
            state='present' if state == 'done' else 'future',
            dt_from=dt_exec,
            dt_until=dt_until,
            obj=to_move.obj)

    @classmethod
    def check_create_conditions(cls, state, dt_execution, destination=None,
                                **kwargs):
        """Ensure that ``destination`` is indeed a container."""
        super(Move, cls).check_create_conditions(state, dt_execution,
                                                 **kwargs)
        if destination is None or not destination.is_container():
            raise OperationContainerExpected(
                cls, "destination field value {offender}",
                offender=destination)

    @classmethod
    def plan_for_outcomes(cls, inputs, outcomes, dt_execution=None, **fields):
        if len(outcomes) != 1:
            raise OperationError(
                cls, "can't plan for {nb_outcomes} outcomes, would need "
                "exactly one outcome. Got {outcomes!r})",
                nb_outcomes=len(outcomes),
                outcomes=outcomes)

        outcome = next(iter(outcomes))
        destination = outcome.location
        cls.check_create_conditions('planned', dt_execution,
                                    inputs=inputs, destination=destination,
                                    **fields)
        move = cls.insert(destination=destination, state='planned',
                          dt_execution=dt_execution, **fields)
        move.link_inputs(inputs)
        outcome.outcome_of = move
        return move

    def execute_planned(self):
        dt_execution = self.dt_execution

        self.input.update(state='past', dt_until=dt_execution)
        self.outcome.update(state='present', dt_from=dt_execution)

    def is_reversible(self):
        """Moves are always reversible.

        See :meth:`the base class <.base.Operation.is_reversible>` for what
        reversibility exactly means.
        """
        return True

    def plan_revert_single(self, dt_execution, follows=()):
        if not follows:
            # reversal of an end-of-chain move
            after = self
        else:
            # A move has at most a single follower, hence
            # its reversal follows at most one operation with one outcome.
            after = next(iter(follows))
        # but nothing guarantees that 'after' is an instance of the
        # single outcome mixin
        return self.create(input=next(iter(after.outcomes)),
                           destination=self.input.location,
                           dt_execution=dt_execution,
                           state='planned',
                           **self.revert_extra_fields())

    def revert_extra_fields(self):
        """Extra fields to take into account in :meth:`plan_revert_single`.

        Singled out for easy subclassing, e.g., by the
        :ref:`wms-quantity Blok <blok_wms_quantity>`.
        """
        return {}

    def input_location_altered(self):
        """A Move doesn't care if its origin changed."""
