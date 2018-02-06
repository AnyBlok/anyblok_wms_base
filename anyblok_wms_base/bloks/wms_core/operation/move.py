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
SingleGoodsSplitter = Declarations.Mixin.WmsSingleGoodsSplitterOperation


@register(Operation)
class Move(SingleGoodsSplitter, Operation):
    """A stock move
    """
    TYPE = 'wms_move'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))
    destination = Many2One(model='Model.Wms.Location')

    def after_insert(self):
        goods = self.goods
        if self.partial or self.state == 'done':
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

    def execute_planned_after_split(self):
        goods = self.goods
        if self.partial:
            # not done by the split, because goods' reason is already the Move
            goods.state = 'present'
            return

        Goods = self.registry.Wms.Goods
        query = Goods.query().filter(Goods.reason == self)
        query.filter(Goods.quantity < 0).delete()

        after_move = query.one()
        after_move.state = 'present'
        self.goods = after_move
        goods.delete()
