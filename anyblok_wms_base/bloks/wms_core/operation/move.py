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


register = Declarations.register
Operation = Declarations.Model.Wms.Operation
Splitter = Declarations.Mixin.WmsSplitterOperation


@register(Operation)
class Move(Splitter, Operation):
    """A stock move
    """
    TYPE = 'wms_move'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))
    destination = Many2One(model='Model.Wms.Location',
                           nullable=False)

    def specific_repr(self):
        return ("input={self.input!r}, "
                "destination={self.destination!r}").format(self=self)

    def after_insert(self):
        state, to_move, dt_exec = self.state, self.input, self.dt_execution

        self.registry.Wms.Goods.Avatar.insert(
            location=self.destination,
            reason=self,
            state='present' if state == 'done' else 'future',
            dt_from=dt_exec,
            # copied fields:
            dt_until=to_move.dt_until,
            goods=to_move.goods)

        to_move.dt_until = dt_exec
        if state == 'done':
            to_move.state = 'past'

    def execute_planned_after_split(self):
        dt_execution = self.dt_execution

        after_move = self.outcomes[0]
        after_move.update(state='present', dt_from=dt_execution)
        self.registry.flush()

        self.input.update(state='past', reason=self, dt_until=dt_execution)

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
            # its reversal follows at most one operation, whose
            # outcome is one Goods record
            after = follows[0]
        return self.create(input=after.outcomes[0],
                           quantity=self.quantity,
                           destination=self.input.location,
                           dt_execution=dt_execution,
                           state='planned')
