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
from anyblok.column import String
from anyblok_postgres.column import Jsonb
from anyblok.relationship import Many2One

register = Declarations.register
Operation = Declarations.Model.Wms.Operation


@register(Operation)
class Arrival(Operation):
    """Operation to describe physical arrival of goods in some location.

    Arrivals store data about the expected or arrived Goods: properties, code,
    quantity… These are copied over to the corresponding Goods records in all
    cases and stay inert after the fact.

    In case the Arrival state is ``planned``,
    these are obviously only unchecked values,
    but in case it is ``done``, the actual meaning can depend
    on the application:

    - maybe the application won't use the ``planned`` state at all, and
      will only create Arrival after checking them,
    - maybe the application will inspect the Arrival properties, compare them
      to reality, update them on the created Goods and cancel downstream
      operations if needed, before calling :meth:`execute`.

    TODO maybe provide higher level facilities for validation scenarios.
    """
    TYPE = 'wms_arrival'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))
    goods_type = Many2One(model='Model.Wms.Goods.Type')
    goods_properties = Jsonb(label="Properties of arrived Goods")
    goods_code = String(label="Code to set on arrived Goods")
    location = Many2One(model='Model.Wms.Location')
    quantity = Decimal(label="Quantity")  # TODO non negativity constraint

    def specific_repr(self):
        return ("goods_type={self.goods_type!r}, "
                "location={self.location!r}, "
                "quantity={self.quantity}").format(self=self)

    @classmethod
    def check_create_conditions(cls, state, **kwargs):
        """An Arrival does not have preconditions."""

    @classmethod
    def find_parent_operations(cls, goods=None, **kwargs):
        """an Arrival does not follow anything."""
        return ()

    def check_execute_conditions(self):
        """An Arrival does not have preconditions."""

    def after_insert(self):
        Goods = self.registry.Wms.Goods
        self_props = self.goods_properties
        if self_props is None:
            props = None
        else:
            props = Goods.Properties.create(**self_props)
        Goods.insert(
            location=self.location,
            quantity=self.quantity,
            reason=self,
            state='present' if self.state == 'done' else 'future',
            type=self.goods_type,
            properties=props,
            code=self.goods_code,
        )

    def execute_planned(self):
        Goods = self.registry.Wms.Goods
        Goods.query().filter(Goods.reason == self).one().update(state='present')

    def cancel_single(self):
        Goods = self.registry.Wms.Goods
        Goods.query().filter(Goods.reason == self).delete(
            synchronize_session='fetch')

    obliviate_single = cancel_single
