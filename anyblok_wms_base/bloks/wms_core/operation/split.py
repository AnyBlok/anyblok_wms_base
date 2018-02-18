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

register = Declarations.register
Operation = Declarations.Model.Wms.Operation
SingleGoods = Declarations.Mixin.WmsSingleGoodsOperation


@register(Operation)
class Split(SingleGoods, Operation):
    """A split of Goods record.

    Splits are operations of a special kind, that have to be considered
    internal details of wms_core, that are not guaranteed to exist in the
    future.

    While non trivial in the database, they may have no physical counterpart in
    the real world : they cut a Record of Goods in two. This can indeed be
    a physical operation if the Goods are meters of wiring for instance, but
    it's only a change in representation if the Goods are individual pieces,
    in which case N>1 records of a given Goods Type with quantity=1 and
    identical properties are strictly equivalent with one record with
    quantity=N. Obviously, in the latter case, moving only one of these N
    Goods needs first a split of the Record.

    We've decided to represent this as an Operation for the sake of
    consistency, and especially to avoid too much special cases in the code.
    The benefit is that they appear explicitely in the history.

    We may introduce in the future markers on the Goods Type model later on
    to indicate if splits are physical or not, and certainly if they can be
    reverted.

    For the time being, a planned split creates two records in 'future' state:

    - the first has a positive quantity and is the one that will persist once
      the split will be executed
    - the second has a quantity being the exact negative of the
      first, so that the operation doesn't biai future on stock levels.

    This is good enough for now, if not entirely satisfactory. Once we have
    visibility time ranges on moves, we might change this and enforce that
    all Goods records have positive quantities.

    As Split records are typically created from other Operation records,
    they are also typically executed from the latter.
    """
    TYPE = 'wms_split'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))
    quantity = Decimal(label="Quantity")  # TODO non negativity constraint

    def specific_repr(self):
        return ("goods={self.goods!r}, "
                "quantity={self.quantity}").format(self=self)

    def after_insert(self):
        """Business logic after the inert insertion

        This method returns the newly (positive) created goods, as a special
        convenience for direct callers within ``wms_core`` Blok.

        Usually downstream code is not supposed to call :meth:``after_insert``
        direcly, but this Operation's siblings are entitled to it (unit tested
        together, and this can spare some verifications).
        """
        self.registry.flush()
        goods = self.goods
        Goods = self.registry.Wms.Goods
        qty = self.quantity
        new_goods = dict(
            location=goods.location,
            reason=self,
            type=goods.type,
            code=goods.code,
            properties=goods.properties,
        )
        if self.state == 'done':
            goods.quantity -= self.quantity
            # Should we update the reason on the original record ?
            # it seems unnecessary, although it sounds true in case of
            # splits having physical meaning : in that case the split is
            # indeed the reason for what can be witnessed in an inventory
            goods.reason = self
            # TODO check for some kind of copy() API on SQLA
            return Goods.insert(quantity=qty, state='present', **new_goods)
        else:
            new_goods['state'] = 'future'
            # TODO check for some kind of copy() API on SQLA
            split = Goods.insert(quantity=qty, **new_goods)
            Goods.insert(quantity=-qty, **new_goods)
            return split

    def get_outcome(self):
        Goods = self.registry.Wms.Goods
        return Goods.query().filter(
            Goods.reason == self).filter(
                Goods.id != self.goods.id).filter(
                    Goods.quantity > 0).one()

    def execute_planned(self):
        self.goods.quantity -= self.quantity
        Goods = self.registry.Wms.Goods
        query = Goods.query().filter(Goods.reason == self)
        query.filter(Goods.quantity < 0).delete(synchronize_session='fetch')
        for created in query.filter(Goods.quantity > 0).all():
            created.state = 'present'

    def cancel_single(self):
        Goods = self.registry.Wms.Goods
        Goods.query().filter(Goods.reason == self).delete(
            synchronize_session='fetch')

    def plan_revert_single(self, follows=()):
        if not follows:
            # reversal of an end-of-chain split
            follows = [self]
        Wms = self.registry.Wms
        Goods = Wms.Goods
        # TODO introduce an outcome() generic API for all operations ?
        # here in that case, that's for multiple operations
        # in_ is not implemented for Many2Ones
        to_aggregate = Goods.query().filter(
            Goods.reason_id.in_(set(f.id for f in follows)),
            Goods.quantity > 0).all()
        goods = self.goods
        if goods not in to_aggregate and goods.state == 'present':
            # our initial goods have not been fully exhausted
            # and hasn't had any downstream operations
            to_aggregate.append(self.goods)
        return Wms.Operation.Aggregate.create(goods=to_aggregate,
                                              state='planned')
