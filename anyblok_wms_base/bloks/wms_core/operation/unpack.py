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


@register(Operation)
class Unpack(Operation):
    """Unpacking some Goods, creating new Goods records.

    What happens during unpacking is specified as behaviours of the
    Goods Type of the Goods being unpacked.

    For the time being, Unpacks will create the new Goods records in the
    same location. Downstream libraries and applications can prepend moves to
    unpacking areas, and/or append moves to final destinations.

    It's possible that we'd introduce an optional 'destination' column
    in the future, if the current schema is too inconvenient or bloats the
    database too much.
    """
    TYPE = 'wms_unpack'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))
    goods = Many2One(model='Model.Wms.Goods', nullable=False)
    quantity = Decimal(label="Quantity")  # TODO non negativity constraint

    @classmethod
    def find_parent_operations(cls, goods=None, **kwargs):
        if goods is None:
            raise ValueError(
                "'goods' kwarg must be passed to Operation.create()")
        return [goods.reason]

    @classmethod
    def check_create_conditions(cls, state, goods=None, quantity=None,
                                **kwargs):
        if goods is None:
            raise ValueError("'goods' kwarg must be passed to Unpack.create()")
        if quantity is None:
            raise ValueError("'quantity' kwarg must be passed "
                             "to Unpack.create()")
        if state == 'done' and goods.state != 'present':
            raise ValueError("Can't create an Unpack in state 'done' "
                             "for goods %r because of their state %r" % (
                                 goods, goods.state))
        assert 'unpack' in goods.type.behaviours

        # TODO specific exceptions
        if quantity > goods.quantity:
            raise ValueError(
                "Can't unpack a greater quantity (%r) "
                "than held in goods %r (which have quantity=%r)" % (
                    quantity, goods, goods.quantity))
        if quantity != goods.quantity:
            raise NotImplementedError(
                "Sorry not able to split Goods records yet")

    def after_insert(self):
        # TODO implement splitting
        Goods = self.registry.Wms.Goods
        GoodsType = Goods.Type
        goods = self.goods

        spec = goods.type.behaviours['unpack']
        type_ids = set(x[0] for x in spec)
        goods_types = {gt.id: gt for gt in GoodsType.query().filter(
                       GoodsType.id.in_(type_ids)).all()}

        if self.state == 'done':
            goods.update(state='past')
            # TODO carry over properties
            for outcome_type_id, outcome_qty in spec:
                Goods.insert(quantity=outcome_qty * self.quantity,
                             location=goods.location,
                             type=goods_types[outcome_type_id],
                             reason=self,
                             state='present')
        else:
            raise NotImplementedError
