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
    """Quantity of the PhysObj to be created.

    It defaults to 1 to help adding ``wms-quantity`` to a codebase.
    """

    @classmethod
    def define_table_args(cls):
        return super(Arrival, cls).define_table_args() + (
            CheckConstraint('quantity > 0',
                            name='positive_qty'),)

    def specific_repr(self):
        return ("physobj_type={self.physobj_type!r}, "
                "location={self.location!r}, "
                "quantity={self.quantity}").format(self=self)

    def after_insert(self):
        # TODO reduce duplication
        PhysObj = self.registry.Wms.PhysObj
        self_props = self.physobj_properties
        if self_props is None:
            props = None
        else:
            props = PhysObj.Properties.create(**self_props)

        goods = PhysObj.insert(type=self.physobj_type,
                               properties=props,
                               quantity=self.quantity,
                               code=self.physobj_code)
        PhysObj.Avatar.insert(
            obj=goods,
            location=self.location,
            outcome_of=self,
            state='present' if self.state == 'done' else 'future',
            dt_from=self.dt_execution,
        )
