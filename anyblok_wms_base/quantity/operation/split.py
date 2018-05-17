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
    OperationQuantityError,
)

register = Declarations.register
Operation = Declarations.Model.Wms.Operation
SingleInput = Declarations.Mixin.WmsSingleInputOperation


@register(Operation)
class Split(SingleInput, Operation):
    """A split of Goods record in two.

    Splits replace their input's :class:`Goods
    <anyblok_wms_base.quantity.goods.Goods>` record with
    two of them, one having the wished :attr:`quantity`, along with
    Avatars at the same location, while
    keeping the same properties and the same total quantity.

    This is therefore destructive for the input's Goods, which is not
    conceptually satisfactory, but will be good enough at this stage of
    development.

    While non trivial in the database, they may have no physical counterpart in
    the real world. We call them *formal* in that case.

    Formal Splits are operations of a special kind, that have to be considered
    internal details of ``wms-core``, that are not guaranteed to exist in the
    future.

    Formal Splits can always be reverted with
    :class:`Aggregate <.aggregate.Aggregate>` Operations,
    but only some physical Splits can be reverted, depending on
    the Goods Type.

    .. seealso:: :class:`Model.Wms.Goods.Type
                 <anyblok_wms_base.quantity.goods.Type>`
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

    Splits are typically created and executed from :class:`Splitter Operations
    <.splitter.WmsSplitterOperation>`, and that explains the
    above-mentioned zero lifespans.
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
        return ("input={self.input!r}, "
                "quantity={self.quantity}").format(self=self)

    def after_insert(self):
        self.registry.flush()
        avatar = self.input
        goods = avatar.goods
        qty = self.quantity
        new_goods = dict(
            type=goods.type,
            code=goods.code,
            properties=goods.properties,
        )
        new_avatars = dict(
            location=avatar.location,
            reason=self,
            dt_from=self.dt_execution,
            dt_until=avatar.dt_until,
        )
        avatar.dt_until = self.dt_execution
        if self.state == 'done':
            avatar.update(state='past', reason=self)
            new_avatars['state'] = 'present'
        else:
            new_avatars['state'] = 'future'

        return tuple(
            avatar.insert(
                goods=goods.insert(quantity=new_qty, **new_goods),
                **new_avatars)
            for new_qty in (qty, goods.quantity - qty))

    @property
    def wished_outcome(self):
        """Return the Goods record with the wished quantity.

        This is only one of :attr:`outcomes
        <anyblok_wms_base.core.operation.base.Operation.outcomes>`

        :rtype: :class:`Wms.Goods
                <anyblok_wms_base.core.goods.Goods>`
        """
        Goods = self.registry.Wms.Goods
        Avatar = Goods.Avatar
        # in case the split is exactly in half, there's no difference
        # between the two records we created, let's pick any.
        outcome = Avatar.query().join(Avatar.goods).filter(
            Avatar.reason == self,
            Avatar.state != 'past',
            Goods.quantity == self.quantity).first()
        if outcome is None:
            raise OperationError(self, "The split outcomes have disappeared")
        return outcome

    def check_execute_conditions(self):
        """Call the base class's version and check that quantity is suitable.
        """
        super(Split, self).check_execute_conditions()
        goods = self.input.goods
        if self.quantity > goods.quantity:
            raise OperationQuantityError(
                self,
                "Can't execute {op}, whose quantity {op.quantity} is greater "
                "than on its input {goods}, "
                "although it's been successfully planned.",
                op=self, goods=self.input)

    def execute_planned(self):
        for outcome in self.outcomes:
            outcome.update(state='present', dt_from=self.dt_execution)
        self.registry.flush()
        self.input.update(state='past', dt_until=self.dt_execution,
                          reason=self)
        self.registry.flush()

    def is_reversible(self):
        """Reversibility depends on the relevant Goods Type.

        See :meth:`on Model.Goods.Type
        <anyblok_wms_base.core.goods.Type.is_split_reversible>`
        """
        return self.input.goods.type.is_split_reversible()

    def plan_revert_single(self, dt_execution, follows=()):
        if not follows:
            # reversal of an end-of-chain split
            follows = [self]
        Wms = self.registry.Wms
        Avatars = Wms.Goods.Avatar
        # here in that case, that's for multiple operations
        # in_ is not implemented for Many2Ones
        reason_ids = set(f.id for f in follows)
        reason_ids.add(self.id)
        to_aggregate = Avatars.query().filter(
            Avatars.reason_id.in_(reason_ids),
            Avatars.state != 'past').all()
        return Wms.Operation.Aggregate.create(inputs=to_aggregate,
                                              dt_execution=dt_execution,
                                              state='planned')

    def obliviate_single(self):
        """Remove the created Goods in addition to base class operation.

        The base class would only take care of the created Avatars
        """
        outcomes_goods = [o.goods for o in self.outcomes]
        super(Split, self).obliviate_single()
        for goods in outcomes_goods:
            goods.delete()
