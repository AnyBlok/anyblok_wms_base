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
class Move(Operation):
    """A stock move
    """
    TYPE = 'wms_move'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))
    goods = Many2One(model='Model.Wms.Goods', nullable=False)
    destination = Many2One(model='Model.Wms.Location')
    quantity = Decimal(label="Quantity")  # TODO non negativity constraint

    @classmethod
    def find_parent_operations(cls, goods=None, **kwargs):
        if goods is None:
            raise ValueError("goods kwarg must be passed to Operation.create()")
        return [goods.reason]

    @classmethod
    def check_create_conditions(cls, state, goods=None, quantity=None,
                                **kwargs):
        if goods is None:
            raise ValueError("goods kwarg must be passed to Move.create()")
        if quantity is None:
            raise ValueError("quantity kwarg must be passed to Move.create()")
        if state == 'done' and goods.state != 'present':
            raise ValueError("Can't create a Move in state 'done' for goods "
                             "%r because of their state %r" % (goods,
                                                               goods.state))
        # TODO specific exception
        if quantity > goods.quantity:
            raise ValueError("Can't move a greater quantity (%r) than held in "
                             "goods %r (which have quantity=%r)" % (
                                 quantity, goods, goods.quantity))
        if quantity != goods.quantity:
            raise NotImplementedError(
                "Sorry not able to split Goods records yet")

    def after_insert(self):
        # TODO implement splitting
        goods = self.goods
        if self.state == 'done':
            # well, yeah, in PostgreSQL, this has about the same cost
            # as copying the row, but at least we don't transmit it
            goods.update(location=self.destination)
            # TODO if I don't flush now, SQLA complains about a circular
            # dependency in final flush (ok, I get it, it needs to order its
            # operations), but it doesn't with a plain insert. I'd prefer
            # not to flush now if possible. Is it possible to give indications?
            # so far for being mildly more efficient, now we have two UPDATE
            # queries…
            self.registry.session.flush()
            goods.update(reason=self)
        else:
            # TODO check for some kind of copy() API on SQLA
            self.registry.Wms.Goods.insert(
                location=self.destination,
                quantity=self.quantity,
                reason=self,
                state='future',
                type=goods.type,
                code=goods.code,
                properties=goods.properties)

    def check_execute_conditions(self):
        goods = self.goods
        if goods.state != 'present':
            raise ValueError("Can't excute a Move for goods "
                             "%r because of their state %r" % (goods,
                                                               goods.state))
        if self.quantity > goods.quantity:
            raise ValueError("Can't move a greater quantity (%r) than held in "
                             "goods %r (which have quantity=%r)" % (
                                 self.quantity, goods, goods.quantity))
        if self.quantity != goods.quantity:
            raise NotImplementedError(
                "Sorry not able to split Goods records yet")

    def execute_planned(self):
        # TODO adapt to splitting
        Goods = self.registry.Wms.Goods
        after_move = Goods.query().filter(Goods.reason == self).one()
        after_move.update(state='present')
        if after_move != self.goods:
            # this should alway be true in case of a move planned, then
            # executed, but let's be safe for now
            self.goods.update(state='past')
