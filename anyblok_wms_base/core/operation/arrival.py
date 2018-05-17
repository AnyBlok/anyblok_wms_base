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
from anyblok.column import String
from anyblok_postgres.column import Jsonb
from anyblok.relationship import Many2One

register = Declarations.register
Operation = Declarations.Model.Wms.Operation


@register(Operation)
class Arrival(Operation):
    """Operation to describe physical arrival of goods in some location.

    Arrivals store data about the expected or arrived Goods: properties, code…
    These are copied over to the corresponding Goods records in all
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
    """Primary key."""
    goods_type = Many2One(model='Model.Wms.Goods.Type')
    """Expected :class:`Goods Type
    <anyblok_wms_base.core.goods.Type>`.
    """
    goods_properties = Jsonb(label="Properties of arrived Goods")
    """Expected :class:`Properties
    <anyblok_wms_base.core.goods.Properties>`.

    They are copied over to the newly created :class:`Goods
    <anyblok_wms_base.core.goods.Goods>` as soon as the Arrival
    is planned, and aren't updated by :meth:`execute`. Matching them with
    reality is the concern of separate validation processes, and this
    field can serve for later assessments after the fact.
    """
    goods_code = String(label="Code to set on arrived Goods")
    """Expected :attr:`Goods code
    <anyblok_wms_base.core.goods.Goods.code>`.

    Can be ``None`` in case the arrival process issues the code only
    at the time of actual arrival.
    """
    location = Many2One(model='Model.Wms.Location')
    """Will be the location of the initial Avatar."""

    inputs_number = 0
    """This Operation is a purely creative one."""

    def specific_repr(self):
        return ("goods_type={self.goods_type!r}, "
                "location={self.location!r}").format(self=self)

    def after_insert(self):
        Goods = self.registry.Wms.Goods
        self_props = self.goods_properties
        if self_props is None:
            props = None
        else:
            props = Goods.Properties.create(**self_props)

        goods = Goods.insert(type=self.goods_type,
                             properties=props,
                             code=self.goods_code)
        Goods.Avatar.insert(
            goods=goods,
            location=self.location,
            reason=self,
            state='present' if self.state == 'done' else 'future',
            dt_from=self.dt_execution,
        )

    def execute_planned(self):
        Avatar = self.registry.Wms.Goods.Avatar
        Avatar.query().filter(Avatar.reason == self).one().update(
            state='present', dt_from=self.dt_execution)
