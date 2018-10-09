# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from sqlalchemy import CheckConstraint

from anyblok import Declarations
from anyblok.column import Boolean
from anyblok.column import Decimal

from anyblok_wms_base.exceptions import (
    OperationQuantityError,
    OperationMissingQuantityError,
)

Mixin = Declarations.Mixin
register = Declarations.register


@register(Mixin)
class WmsSplitterOperation:
    """Mixin for operations on a single input that can split.

    This is to be applied after :class:`Mixin.WmsSingleInputOperation
    <anyblok_wms_base.core.operation.single_input.WmsSingleInputOperation>`.
    Use :class:`WmsSplitterSingleInputOperation` to get both at once.

    It defines the :attr:`quantity` field to express that the Operation only
    works on some of the quantity held by the PhysObj of the single input.

    In case the Operation's :attr:`quantity` is less than in the PhysObj
    record, a :class:`Split <.split.Split>` will be inserted properly in
    history, and the Operation implementation can ignore quantities
    completely, as it will always, in truth, work on the whole of the input
    it will see.

    Subclasses can use the :attr:`partial` field if they need to know
    if that happened, but this should be useful only in special cases.
    """
    quantity = Decimal(default=1)
    """The quantity this Operation will work on.

    Can be less than the quantity of our single input.
    """

    partial = Boolean(label="Operation induced a split")
    """Record if a Split will be or has been inserted in the history.

    Such insertions should happen if the operation's original PhysObj
    have greater quantity than the operation needs.

    This is useful because once the Split is executed,
    this information can't be deduced from the quantities involved any more.
    """

    @classmethod
    def define_table_args(cls):
        return super(
            WmsSplitterOperation, cls).define_table_args() + (
                CheckConstraint('quantity > 0', name='positive_qty'),
            )

    def specific_repr(self):
        return ("input={self.input!r}, "
                "quantity={self.quantity}").format(self=self)

    @classmethod
    def check_create_conditions(cls, state, dt_execution,
                                inputs=None, quantity=None, **kwargs):

        super(WmsSplitterOperation, cls).check_create_conditions(
            state, dt_execution,
            inputs=inputs, quantity=quantity, **kwargs)

        goods = inputs[0].goods
        if quantity is None:
            raise OperationMissingQuantityError(
                cls,
                "The 'quantity keyword argument must be passed to "
                "the create() method")
        if quantity > goods.quantity:
            raise OperationQuantityError(
                cls,
                "Can't split a greater quantity ({op_quantity}) than held in "
                "{input} (which have quantity={input.goods.quantity})",
                op_quantity=quantity, input=inputs[0])

    def check_execute_conditions(self):
        """Check that the quantity (after possible Split) is as on the input.

        If a Split has been inserted, then this calls the base class
        for the input of the Split, instead of ``self``, because the input of
        ``self`` is in that case the outcome of the Split, and it's normal
        that it's in state ``future``: the Split will be executed during
        ``self.execute()``, which comes once the present method has agreed.
        """
        goods = self.input.goods
        if self.quantity != goods.quantity:
            raise OperationQuantityError(
                self,
                "Can't execute planned for a different quantity {op_quantity} "
                "than held in its input {input} "
                "(which have quantity={goods.quantity}). "
                "If it's less, a Split should have occured first ")
        if self.partial:
            self.input.reason.check_execute_conditions()
        else:
            super(WmsSplitterOperation,
                  self).check_execute_conditions()

    @classmethod
    def before_insert(cls, state='planned', follows=None, inputs=None,
                      quantity=None, dt_execution=None, dt_start=None,
                      **kwargs):
        """Override to introduce a Split if needed

        In case the value of :attr:`quantity` does not match the one from the
        ``goods`` field, a :class:`Split <.split.Split>` is inserted
        transparently in the history, as if it'd been there in the first place:
        subclasses can implement :meth:`after_insert` as if the quantities were
        matching from the beginning.
        """
        avatar = inputs[0]
        partial = quantity < avatar.goods.quantity
        if not partial:
            return inputs, None

        Split = cls.registry.Wms.Operation.Split
        split = Split.create(input=avatar, quantity=quantity, state=state,
                             dt_execution=dt_execution)
        return [split.wished_outcome], dict(partial=partial)

    def execute_planned(self):
        """Execute the :class:`Split <.split.Split>` if any, then self."""
        if self.partial:
            split_op = self.follows[0]
            split_op.execute(dt_execution=self.dt_execution)
        super(WmsSplitterOperation, self).execute_planned()
        self.registry.flush()


Operation = Declarations.Model.Wms.Operation
Splitter = Declarations.Mixin.WmsSplitterOperation


@register(Mixin)
class WmsSplitterSingleInputOperation(Splitter):
    """Use this mixin to get both ``SingleInput`` and ``Splitter`` at once."""


@register(Operation)
class Move(Splitter):
    """Override making Move a splitter operation.
    """


@register(Operation)
class Departure(Splitter):
    """Override making Departure a Splitter Operation.

    As with all :class:`Splitter Operations
    <anyblok_wms_base.quantity.operation.splitter.WmsSplitterOperation>`,
    Departures can be partial, i.e.,
    there's no need to match the exact quantity held in the underlying PhysObj
    record: an automatic Split will occur if needed.

    In many scenarios, the Departure would come after a
    :ref:`Move <op_move>` that would bring
    the goods to a shipping location and maybe issue itself a
    :ref:`Split <op_split_aggregate>`, so that
    actually the quantity for departure would be an exact match, but Departure
    does not rely on that.
    """


@register(Operation)
class Unpack(Splitter):
    """Override making Unpack a splitter operation.
    """
