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
from anyblok.column import Decimal

from anyblok_wms_base.exceptions import (
    OperationError,
)

register = Declarations.register
Operation = Declarations.Model.Wms.Operation
SingleGoods = Declarations.Mixin.WmsSingleGoodsOperation


@register(Operation)
class Split(SingleGoods, Operation):
    """A split of Goods record in two.

    Splits replace a :class:`Goods <.goods.Goods>` record with two of them,
    keeping the same properties and location, and the same total
    quantity.

    While non trivial in the database, they may have no physical counterpart in
    the real world. We call them *formal* in that case.

    Formal Splits are operations of a special kind, that have to be considered
    internal details of ``wms-core``, that are not guaranteed to exist in the
    future.

    Formal Splits can always be reverted with
    :class:`Aggregate <.aggregate.Aggregate>` Operations,
    but only some physical Splits can be reverted, depending on
    the Goods Type.

    .. seealso:: :class:`Model.Wms.Goods.Type <..goods.Type>`
                 for a full discussion including use-cases of formal and
                 physical splits and reversal of the latter.

    In the formal case, we've decided to represent this as an Operation for
    the sake of consistency, and especially to avoid too much special cases
    in implementation of various concrete Operations.

    The benefit is that Splits appear explicitely in the history, and this
    helps implementing :ref:`history manipulating methods
    <op_cancel_revert_obliviate>` a lot.

    The drawback is that we get a proliferation of Goods records, some of them
    even with a zero second lifespan, but even those could be simplified only
    for executed Splits.

    Splits are typically created and executed from :class:`splitter Operations
    <.splitter.WmsSingleGoodsSplitterOperation>`, and that explains the
    above-mentioned zero lifespans.

    For Splits, the :attr:`quantity
    <.on_goods.WmsSingleGoodsOperation.quantity>` field is the one the issuer
    wants to extract.
    """
    TYPE = 'wms_split'
    """Polymorphic key"""

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))

    quantity = Decimal()
    """The quantity to split."""

    def specific_repr(self):
        return ("goods={self.goods!r}, "
                "quantity={self.quantity}").format(self=self)

    def after_insert(self):
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

    @property
    def wished_outcome(self):
        """Return the Goods record with the wished quantity.

        This is only one of ``self.outcome``

        :rtype: Goods
        """
        Goods = self.registry.Wms.Goods
        # in case the split is exactly in half, there's no difference
        # between the two records we created, let's pick any.
        outcome = Goods.query().filter(Goods.reason == self,
                                       Goods.state != 'past',
                                       Goods.quantity == self.quantity).first()
        if outcome is None:
            raise OperationError(self, "The split outcomes have disappeared")
        return outcome

    def execute_planned(self):
        Goods = self.registry.Wms.Goods
        for outcome in Goods.query().filter(Goods.reason == self).all():
            outcome.update(state='present',
                           dt_from=self.dt_execution,
                           )
#                           dt_until=self.orig_goods_dt_until)
        self.registry.flush()
        self.goods.update(state='past', dt_until=self.dt_execution, reason=self)
        self.registry.flush()

    def cancel_single(self):
        Goods = self.registry.Wms.Goods
        Goods.query().filter(Goods.reason == self).delete(
            synchronize_session='fetch')

    def obliviate_single(self):
        self.reset_goods_original_values()
        self.registry.flush()
        Goods = self.registry.Wms.Goods
        Goods.query().filter(Goods.reason == self).delete(
            synchronize_session='fetch')

    def is_reversible(self):
        """Reversibility depends on the relevant Goods Type.

        See :meth:`on Model.Goods.Type
        <anyblok_wms_base.bloks.wms_core.goods.Type.is_split_reversible>`
        """
        return self.goods.type.is_split_reversible()

    def plan_revert_single(self, dt_execution, follows=()):
        if not follows:
            # reversal of an end-of-chain split
            follows = [self]
        Wms = self.registry.Wms
        Goods = Wms.Goods
        # here in that case, that's for multiple operations
        # in_ is not implemented for Many2Ones
        reason_ids = set(f.id for f in follows)
        reason_ids.add(self.id)
        to_aggregate = Goods.query().filter(
            Goods.reason_id.in_(reason_ids),
            Goods.state != 'past').all()
        return Wms.Operation.Aggregate.create(working_on=to_aggregate,
                                              dt_execution=dt_execution,
                                              state='planned')
