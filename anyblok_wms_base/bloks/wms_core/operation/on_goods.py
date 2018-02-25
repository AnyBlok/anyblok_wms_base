# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
"""Mixins for Operations that take some Goods as inputs and operate on them.

In principle, this would apply to all except purely creating operations.
It's quite possible, if not recommended, to have special Operations inputting
Goods yet not using these Mixins.
"""
from sqlalchemy import CheckConstraint

from anyblok import Declarations
from anyblok.column import Decimal
from anyblok.column import Integer
from anyblok.column import DateTime
from anyblok.relationship import Many2One
from anyblok.relationship import Many2Many

from anyblok_wms_base.exceptions import (
    OperationGoodsError,
    OperationMissingGoodsError,
    OperationQuantityError,
)

Mixin = Declarations.Mixin


@Declarations.register(Declarations.Model.Wms.Operation)
class WorkingOn:
    """Internal table to help reconcile followed operations with their goods.

    For Operations with multiple goods, tracking the followed operations and
    the goods is not enough: we also need to record the original association
    between them.
    use case: oblivion.

    TODO this can probably be done by enriching the ``follows`` Many2Many
    ifself, but that's a bit more complicated at first glance (would
    certainly look more consistent though)
    """
    # TODO apparently, I can't readily construct a multiple primary key
    # from the m2o relationships
    id = Integer(primary_key=True)
    goods = Many2One(model='Model.Wms.Goods',
                     foreign_key_options={'ondelete': 'cascade'})
    quantity = Decimal(label="Quantity")
    acting_op = Many2One(model='Model.Wms.Operation',
                         index=True,
                         foreign_key_options={'ondelete': 'cascade'})
    orig_reason = Many2One(model='Model.Wms.Operation',
                           foreign_key_options={'ondelete': 'cascade'})
    orig_dt_until = DateTime(label="Original dt_until of goods")
    """Saving the original ``dt_until`` value of the Goods

    This is needed to implement :ref:`oblivion op_revert_cancel_obliviate`

    TODO we hope to supersede this while implementing
    :ref:`Avatars <improvement_avatars>`.
    """
    @classmethod
    def define_table_args(cls):
        return super(WorkingOn, cls).define_table_args() + (
            CheckConstraint('quantity > 0', name='positive_qty'),
        )


@Declarations.register(Mixin)
class WmsGoodsOperation:
    """Mixin for operations that apply to a several records of Goods.

    We'll use :class:`Model.Wms.Operation.WorkingOn <WorkingOn>` as an enriched
    Many2Many relationship with the Goods.

    TODO should be simply merged into
    :class:`Model.Wms.Operation <.base.Operation>`
    """

    goods = Many2Many(model='Model.Wms.Goods',
                      join_table='wms_operation_workingon',
                      m2m_remote_columns='goods_id',
                      m2m_local_columns='acting_op_id',
                      label="Goods record to apply the operation to")

    @classmethod
    def find_parent_operations(cls, goods=None, **kwargs):
        return set(g.reason for g in goods)

    @classmethod
    def check_create_conditions(cls, state, dt_execution, goods=None, **kwargs):
        if not goods:
            raise OperationMissingGoodsError(
                cls,
                "The 'goods' keyword argument must be passed to the create() "
                "method, and must not be empty")

        if state == 'done':
            for record in goods:
                if record.state != 'present':
                    raise OperationGoodsError(
                        cls,
                        "Can't create in state 'done' for goods {goods} "
                        "because one of them (id={record.id}) has state "
                        "{record.state} instead of the expected 'present'",
                        goods=goods, record=record)
        # TODO check quantities

    def check_execute_conditions(self):
        for record in self.goods:
            if record.state != 'present':
                raise OperationGoodsError(
                    self,
                    "Can't execute {op} for goods {goods} "
                    "because one of them (id={record.id}) has state "
                    "{record.state} instead of the expected 'present'",
                    goods=self.goods, record=record)

    @classmethod
    def insert(cls, goods=None, **kwargs):
        """Helper to pass goods directly, and take care of follow details.

        :param goods: any iterable of Goods records.
        TODO this is band-aid for the follow details, which should be handled
        otherwise.
        """
        op = super(WmsGoodsOperation, cls).insert(**kwargs)
        working_on = cls.registry.Wms.Operation.WorkingOn
        for record, quantity in goods.items():
            working_on.insert(goods=record,
                              acting_op=op,
                              orig_reason=record.reason,
                              orig_dt_until=record.dt_until)
        return op

    def iter_goods_original_values(self):
        """List incoming goods together with original values kept in WorkingOn.

        Depending on the needs, it might be interesting to avoid
        actually fetching all those records.

        :return: a generator of pairs (goods, their original reasons,
        their original ``dt_until``)
        """
        WorkingOn = self.registry.Wms.Operation.WorkingOn
        # TODO simple 2-column query instead
        return ((wo.goods, wo.orig_reason, wo.orig_dt_until)
                for wo in WorkingOn.query().filter(
                        WorkingOn.acting_op == self).all())

    def reset_goods_original_values(self, state=None):
        """Reset all input Goods to their original reason and state if passed.

        :param state: if not None, will be state on the input Goods

        The original values are those currently held in
        :class:`Model.Wms.Operation.WorkingOn <WorkingOn>`.

        TODO PERF: it should be more efficient not to fetch the goods and
        their records, but work directly on ids (and maybe do this in one pass
        with a clever UPDATE query).
        TODO: consider generalization to the base class to simplify
        implementation of all Operation subclasses.
        """
        for goods, reason in self.iter_goods_original_reasons():
            if state is not None:
                goods.state = state
            goods.reason = reason


@Declarations.register(Mixin)
class WmsSingleGoodsOperation(WmsGoodsOperation):
    """Mixin for operations that apply to a single record of Goods."""

    @classmethod
    def check_create_conditions(cls, state, dt_execution,
                                goods=None, **kwargs):
        super(WmsSingleGoodsOperation, cls).check_create_condition(
            cls, state, dt_execution, goods=None, **kwargs)
        if len(goods) > 1:
            raise OperationGoodsError(
                cls,
                "Takes exactly one Goods record, got {goods}", goods=goods)

    def check_execute_conditions(self):
        goods = self.goods
        if self.quantity > goods.quantity:
            raise OperationQuantityError(
                self,
                "Can't execute {op} with quantity {op.qty} on goods {goods} "
                "(which have quantity={goods.quantity}), "
                "although it's been successfully planned.",
                op=self, goods=self.goods)

        if goods.state != 'present':
            raise OperationGoodsError(
                self,
                "Can't execute for goods {goods} "
                "because their state {state} is not 'present'",
                goods=goods,
                state=goods.state)
