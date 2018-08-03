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
from anyblok.column import Text
from anyblok_postgres.column import Jsonb
from anyblok.relationship import Many2One

from anyblok_wms_base.exceptions import OperationForbiddenState

register = Declarations.register
Operation = Declarations.Model.Wms.Operation


@register(Operation)
class Apparition(Operation):
    """Inventory Operation to record unexpected Goods

    This is similar to Arrival, but has a distinct functional meaning.
    Apparitions can exist only in the ``done`` :ref:`state <op_states>`.

    Another difference with Arrivals is that Apparitions have a
    :attr:`quantity` field.
    """
    TYPE = 'wms_apparition'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))
    """Primary key."""
    goods_type = Many2One(model='Model.Wms.Goods.Type')
    """Observed :class:`Goods Type
    <anyblok_wms_base.core.goods.Type>`.
    """
    quantity = Integer()
    """The number of identical Goods that have appeared.

    Here, identical means "same type, code and properties"
    """
    goods_properties = Jsonb()
    """Observed :class:`Properties
    <anyblok_wms_base.core.goods.Properties>`.

    They are copied over to the newly created :class:`Goods
    <anyblok_wms_base.core.goods.Goods>`. Then the Properties can evolve on
    the Goods, while this Apparition field will keep the exact values
    that were observed during inventory.
    """
    goods_code = Text()
    """Observed :attr:`Goods code
    <anyblok_wms_base.core.goods.Goods.code>`.
    """
    location = Many2One(model='Model.Wms.Goods')
    """Location of appeared Goods.

    This will be the location of the initial Avatars.
    """

    inputs_number = 0
    """This Operation is a purely creative one."""

    def specific_repr(self):
        return ("goods_type={self.goods_type!r}, "
                "location={self.location!r}").format(self=self)

    @classmethod
    def check_create_conditions(cls, state, dt_execution, **kwargs):
        """Forbid creation with wrong states.

        :raises: :class:`OperationForbiddenState
                 <anyblok_wms_base.exceptions.OperationForbiddenState>`
                 if state is not ``'done'``
        """
        if state != 'done':
            raise OperationForbiddenState(
                cls, "Apparition can exist only in the 'done' state",
                forbidden=state)
        super(Apparition, cls).check_create_conditions(
            state, dt_execution, **kwargs)

    def after_insert(self):
        """Create the Goods and their Avatars.

        In the ``wms-core`` implementation, the :attr:`quantity` field
        gives rise to as many Goods records.
        """
        Goods = self.registry.Wms.Goods
        self_props = self.goods_properties
        if self_props is None:
            props = None
        else:
            props = Goods.Properties.create(**self_props)

        for _ in range(self.quantity):
            goods = Goods.insert(type=self.goods_type,
                                 properties=props,
                                 code=self.goods_code)
            Goods.Avatar.insert(goods=goods,
                                location=self.location,
                                reason=self,
                                state='present',
                                dt_from=self.dt_execution)
