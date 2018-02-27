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


@Declarations.register(Mixin)
class WmsSingleGoodsSplitterOperation(Mixin.WmsSingleInputOperation):
    """Mixin for operations on a single record of Goods that can split.

    In case the value of :attr:`quantity` is less than in the Goods record,
    a :class:`Split <.split.Split>` will be inserted properly in history.

    Subclasses can use :attr:`partial` if they need to know if that happened,
    but this should be useful only in very special cases.
    """
    quantity = Decimal()
    """The quantity this Operation will work on.

    Can be less than the quantity of our single Goods record.
    """

    partial = Boolean(label="Operation induced a split")
    """Record if a Split will be or has been inserted in the history.

    Such insertions should happen if the operation's original Goods
    have greater quantity than the operation needs.

    This is useful because once the Split is executed,
    this information can't be deduced from the quantities involved any more.
    """

    @classmethod
    def define_table_args(cls):
        return super(
            WmsSingleGoodsSplitterOperation, cls).define_table_args() + (
                CheckConstraint('quantity > 0', name='positive_qty'),
            )

    def specific_repr(self):
        return ("input={self.input!r}, "
                "quantity={self.quantity}").format(self=self)

    @classmethod
    def check_create_conditions(cls, state, dt_execution,
                                inputs=None, quantity=None, **kwargs):

        super(WmsSingleGoodsSplitterOperation, cls).check_create_conditions(
            state, dt_execution,
            inputs=inputs, quantity=quantity, **kwargs)

        goods = inputs[0]
        if quantity is None:
            raise OperationMissingQuantityError(
                cls,
                "The 'quantity keyword argument must be passed to "
                "the create() method")
        if quantity > goods.quantity:
            raise OperationQuantityError(
                cls,
                "Can't split a greater quantity ({op_quantity}) than held in "
                "{input} (which have quantity={input.quantity})",
                op_quantity=quantity, input=goods)

    def check_execute_conditions(self):
        """Check that the quantity (after possible Split) is as on the input.

        If a Split has been inserted, then this calls the base class
        for the input of the Split, instead of ``self``, because the input of
        ``self`` is in that case the outcome of the Split, and it's normal
        that it's in state ``future``: the Split will be executed during
        ``self.execute()``, which comes once the present method has agreed.
        """
        goods = self.input
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
            super(WmsSingleGoodsSplitterOperation,
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
        goods = inputs[0]
        partial = quantity < goods.quantity
        if not partial:
            return inputs, None

        Split = cls.registry.Wms.Operation.Split
        split = Split.create(input=goods, quantity=quantity, state=state,
                             dt_execution=dt_execution)
        return [split.wished_outcome], dict(partial=partial)

    def execute_planned(self):
        """Execute the :class:`Split <.split.Split>` if any, then self."""
        if self.partial:
            split_op = self.follows[0]
            split_op.execute(dt_execution=self.dt_execution)
        self.execute_planned_after_split()
        self.registry.flush()

    def execute_planned_after_split(self):
        """Part of the execution that occurs maybe after a Split.

        Subclasses can implement this method exactly as if they were
        implementing :meth:`execute_planned <.base.Operation.execute_planned>`.

        If a :class:`Split <.split.Split>` has been inserted in the history,
        it is already executed.
        """
        raise NotImplementedError(
            "for %s" % self.__registry_name__)  # pragma: no cover
