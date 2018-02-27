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
Operation = Declarations.Model.Wms.Operation
SingleGoodsSplitter = Declarations.Mixin.WmsSingleGoodsSplitterOperation


@register(Operation)
class Departure(SingleGoodsSplitter, Operation):
    """Operation to represent Goods physically leaving the system.

    Departures can be partial, i.e., there's no need to match the exact
    quantity held in the Goods record. An automatic Split will occur if needed.

    In many scenarios, the departure would come after a Move that would bring
    the Goods to ship to a shipping location, and maybe issue a Split, so that
    actually the quantity for departure would be an exact match. Yet wms-core's
    Departure operation has no limitation in that regard.

    Downstream libraries and applications can enhance this model
    with additional information (e.g., a shipping address) if needed, although
    it's probably a better design for rich shipment representation to issue
    separate Models and relation tables.
    """
    TYPE = 'wms_departure'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))

    def depart(self):
        """Common logic for final departure step."""
        self.input.update(state='past', reason=self,
                          dt_until=self.dt_execution)

    def after_insert(self):
        """Either finish right away, or represent the future decrease."""
        self.registry.flush()
        if self.state == 'done':
            self.depart()
        else:
            self.input.dt_until = self.dt_execution

    def execute_planned_after_split(self):
        self.registry.flush()
        self.depart()

    def cancel_single(self):
        self.reset_inputs_original_values()

    def obliviate_single(self):
        self.reset_inputs_original_values(state='present')
        self.registry.flush()
