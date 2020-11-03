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

register = Declarations.register
Mixin = Declarations.Mixin
Operation = Declarations.Model.Wms.Operation


@register(Operation)
class Disparition(Mixin.WmsSingleInputOperation,
                  Mixin.WmsInventoryOperation,
                  Operation):
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

    def after_insert(self):
        """Put the input Avatar in the 'past' state
        """
        self.input.state = 'past'

    def obliviate_single(self):
        self.reset_inputs_original_values(state='present')
        self.registry.flush()
