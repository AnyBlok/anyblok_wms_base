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

from anyblok_wms_base.exceptions import OperationForbiddenState

register = Declarations.register
Mixin = Declarations.Mixin
Operation = Declarations.Model.Wms.Operation


@register(Operation)
class Disparition(Mixin.WmsSingleInputOperation, Operation):
    """Inventory Operation to record unexpected loss of PhysObj

    This is similar to Departure, but has a distinct functional meaning.
    Disparitions can exist only in the ``done`` :ref:`state <op_states>`.
    """
    TYPE = 'wms_disparition'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))
    """Primary key."""

    @classmethod
    def check_create_conditions(cls, state, dt_execution, **kwargs):
        """Forbid creation with wrong states.

        :raises: :class:`OperationForbiddenState
                 <anyblok_wms_base.exceptions.OperationForbiddenState>`
                 if state is not ``'done'``

        TODO make a common Mixin for all inventory Operations.
        """
        if state != 'done':
            raise OperationForbiddenState(
                cls, "Apparition can exist only in the 'done' state",
                forbidden=state)
        super(Disparition, cls).check_create_conditions(
            state, dt_execution, **kwargs)

    def after_insert(self):
        """Put the input Avatar in the 'past' state
        """
        self.input.update(dt_until=self.dt_execution,
                          state='past')

    def obliviate_single(self):
        self.reset_inputs_original_values(state='present')
        self.registry.flush()
