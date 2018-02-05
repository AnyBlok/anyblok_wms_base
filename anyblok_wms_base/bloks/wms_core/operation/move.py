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
from anyblok.relationship import Many2One

register = Declarations.register
Operation = Declarations.Model.Wms.Operation
SingleGoods = Declarations.Mixin.WmsSingleGoodsOperation


@register(Operation)
class Move(SingleGoods, Operation):
    """A stock move
    """
    TYPE = 'wms_move'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))
    destination = Many2One(model='Model.Wms.Location')

    def after_insert(self):
        partial = self.quantity < self.goods.quantity
        if partial:
            # TODO maybe override create() itself at this point
            # it's simpler than **inserting** the split in the history
            Split = self.registry.Wms.Operation.Split
            split = Split.insert(goods=self.goods, quantity=self.quantity,
                                 state=self.state)
            split.follows.append(self.goods.reason)
            self.follows.pop()
            self.follows.append(split)
            self.registry.flush()
            self.goods = split.after_insert()

        goods = self.goods
        if partial or self.state == 'done':
            # well, yeah, in PostgreSQL, this has about the same cost
            # as copying the row, but at least we don't transmit it
            goods.update(location=self.destination)
            # TODO if I don't flush now, SQLA complains about a circular
            # dependency in final flush (ok, I get it, it needs to order its
            # operations), but it doesn't with a plain insert. I'd prefer
            # not to flush now if possible. Is it possible to give indications?
            # so far for being mildly more efficient, now we have two UPDATE
            # queries…
            self.registry.flush()
            goods.update(reason=self)
        else:
            fields = dict(reason=self,
                          state='future',
                          type=goods.type,
                          code=goods.code,
                          properties=goods.properties)
            Goods = self.registry.Wms.Goods
            Goods.insert(location=self.destination,
                         quantity=self.quantity,
                         **fields)
            Goods.insert(location=goods.location,
                         quantity=-self.quantity,
                         **fields)

    def check_execute_conditions(self):
        goods = self.goods
        if self.quantity != goods.quantity:
            raise ValueError(
                "Can't move a different quantity (%r) than held in "
                "goods %r (which have quantity=%r). For lesser quantities "
                "a split should have occured first " % (
                    self.quantity, goods, goods.quantity))

    def execute_planned(self):
        Goods = self.registry.Wms.Goods
        goods = self.goods
        follows = self.follows
        split = follows[0] if len(follows) == 1 else None
        # TODO stronger criteria that the split has been induced by the
        # present move
        if split and split.type == 'wms_split' and split.state != 'done':
            split.execute()
            # This Move took responsibility for goods' state by setting
            # itself as reason, split.execute() can't see it any more
            goods.state = 'present'
        else:
            Goods.query().filter(
                Goods.reason == self).filter(Goods.quantity < 0).delete()

        if goods.state != 'present':
            raise ValueError("Can't execute a Move for goods "
                             "%r because of their state %r" % (goods,
                                                               goods.state))

        after_move = Goods.query().filter(Goods.reason == self).one()
        after_move.update(state='present')
        before_move = self.goods
        if after_move != before_move:
            self.goods = after_move
            self.registry.flush()
            before_move.delete()
        self.registry.flush()
