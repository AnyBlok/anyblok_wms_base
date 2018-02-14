# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.

from anyblok import Declarations
from anyblok.column import Decimal
from anyblok.column import Integer
from anyblok.relationship import Many2One

register = Declarations.register
Operation = Declarations.Model.Wms.Operation
SingleGoodsSplitter = Declarations.Mixin.WmsSingleGoodsSplitterOperation


@register(Operation)
class Departure(SingleGoodsSplitter, Operation):
    """Operation to describe physical departure of goods

    This does not encompass all "removals" of goods : only those that due
    to shipping to the outside.

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
    goods = Many2One(model='Model.Wms.Goods')
    quantity = Decimal(label="Quantity")  # TODO non negativity constraint

    def depart(self):
        """Common logic for final departure step."""
        self.registry.flush()
        self.goods.update(state='past', reason=self)
        # TODO dates

    def after_insert(self):
        """Either finish right away, or represent the future decrease."""
        if self.state == 'done':
            return self.depart()

        Goods = self.registry.Wms.Goods
        goods = self.goods
        # TODO copy
        Goods.insert(location=goods.location,
                     quantity=-self.quantity,
                     reason=self,
                     state='future',
                     type=goods.type,
                     code=goods.code,
                     properties=goods.properties)

    def execute_planned_after_split(self):
        Goods = self.registry.Wms.Goods
        Goods.query().filter(Goods.reason == self, Goods.quantity < 0).delete(
            synchronize_session='fetch')
        self.depart()

    def cancel_single(self):
        Goods = self.registry.Wms.Goods
        Goods.query().filter(Goods.reason == self).delete(
            synchronize_session='fetch')
