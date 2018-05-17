# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from sqlalchemy import CheckConstraint

from anyblok import Declarations
from anyblok.column import Decimal

register = Declarations.register
Operation = Declarations.Model.Wms.Operation


@register(Operation)
class Arrival:
    """Override to add the :attr:`quantity` field.
    """

    quantity = Decimal(default=1)
    """Quantity of the Goods to be created.

    It defaults to 1 to help adding ``wms-quantity`` to a codebase.
    """

    @classmethod
    def define_table_args(cls):
        return super(Arrival, cls).define_table_args() + (
            CheckConstraint('quantity > 0',
                            name='positive_qty'),)

    def specific_repr(self):
        return ("goods_type={self.goods_type!r}, "
                "location={self.location!r}, "
                "quantity={self.quantity}").format(self=self)

    def after_insert(self):
        # TODO reduce duplication
        Goods = self.registry.Wms.Goods
        self_props = self.goods_properties
        if self_props is None:
            props = None
        else:
            props = Goods.Properties.create(**self_props)

        goods = Goods.insert(type=self.goods_type,
                             properties=props,
                             quantity=self.quantity,
                             code=self.goods_code)
        Goods.Avatar.insert(
            goods=goods,
            location=self.location,
            reason=self,
            state='present' if self.state == 'done' else 'future',
            dt_from=self.dt_execution,
        )
