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

from anyblok_wms_base.exceptions import (
    OperationError,
)

register = Declarations.register
Operation = Declarations.Model.Wms.Operation
SingleGoods = Declarations.Mixin.WmsSingleGoodsOperation


@register(Operation)
class Split(SingleGoods, Operation):
    """A split of Goods record.

    Splits are operations of a special kind, that have to be considered
    internal details of wms_core, that are not guaranteed to exist in the
    future.

    They replace a Goods record with several ones keeping
    the same properties and locations, and the same total quantity.

    While non trivial in the database, they may have no physical counterpart in
    the real world. We call them *formal* in that case.

    Formal Splits can always be reverted with Aggregate
    Operations, but only some physical Splits can be reverted, depending on
    the Goods Type. See :class:`Model.Wms.Goods.Type` for a full discussion of
    this, with use cases.

    In the formal case, we've decided to represent this as an Operation for
    the sake of consistency, and especially to avoid too much special cases
    in implementation of various Operations.
    The benefit is that Splits appear explicitely in the history.

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

        This method returns the pair of newly created goods, as a special
        convenience for direct callers within ``wms_core`` Blok.
        The first one is the one having the wished quantity.

        Usually downstream code is not supposed to call :meth:``after_insert``
        direcly, but this Operation's siblings are entitled to it (unit tested
        together, and this can spare some verifications).
        """
        self.orig_goods_dt_until = self.goods.dt_until
        self.registry.flush()
        goods = self.goods
        Goods = self.registry.Wms.Goods
        qty = self.quantity
        new_goods = dict(
            location=goods.location,
            reason=self,
            type=goods.type,
            code=goods.code,
            dt_from=self.dt_execution,
            dt_until=goods.dt_until,
            properties=goods.properties,
        )
        goods.dt_until = self.dt_execution
        if self.state == 'done':
            goods.update(state='past', reason=self)
            new_goods['state'] = 'present'
        else:
            new_goods['state'] = 'future'

        return (Goods.insert(quantity=qty, **new_goods),
                Goods.insert(quantity=goods.quantity - qty, **new_goods))

    def get_outcome(self):
        Goods = self.registry.Wms.Goods
        # in case the split is exactly in half, there's no difference
        # between the two records we created, let's pick any.
        outcome = Goods.query().filter(Goods.reason == self,
                                       Goods.quantity == self.quantity).first()
        if outcome is None:
            raise OperationError(self, "The split outcomes have disappeared")
        return outcome

    def execute_planned(self):
        Goods = self.registry.Wms.Goods
        for outcome in Goods.query().filter(Goods.reason == self).all():
            outcome.update(state='present',
                           dt_from=self.dt_execution,
                           dt_until=self.orig_goods_dt_until)
        self.registry.flush()
        self.goods.update(state='past', dt_until=self.dt_execution, reason=self)
        self.registry.flush()

    def cancel_single(self):
        Goods = self.registry.Wms.Goods
        Goods.query().filter(Goods.reason == self).delete(
            synchronize_session='fetch')

    def obliviate_single(self):
        Goods = self.registry.Wms.Goods
        Goods.query().filter(Goods.reason == self,
                             Goods.state == 'past').one().update(
                                 dt_until=self.orig_goods_dt_until,
                                 reason=self.follows[0])
        self.registry.flush()
        Goods = self.registry.Wms.Goods
        Goods.query().filter(Goods.reason == self).delete(
            synchronize_session='fetch')

    def is_reversible(self):
        """Reversibility depends on the relevant Goods Type.

        See :class:`Operation` for what reversibility exactly means in that
        context.
        """
        return self.goods.type.is_split_reversible()

    def plan_revert_single(self, dt_execution, follows=()):
        if not follows:
            # reversal of an end-of-chain split
            follows = [self]
        Wms = self.registry.Wms
        Goods = Wms.Goods
        # TODO introduce an outcome() generic API for all operations ?
        # here in that case, that's for multiple operations
        # in_ is not implemented for Many2Ones
        reason_ids = set(f.id for f in follows)
        reason_ids.add(self.id)
        to_aggregate = Goods.query().filter(
            Goods.reason_id.in_(reason_ids),
            Goods.state != 'past').all()
        return Wms.Operation.Aggregate.create(goods=to_aggregate,
                                              dt_execution=dt_execution,
                                              state='planned')
