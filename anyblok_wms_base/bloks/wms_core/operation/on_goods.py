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
from anyblok import Declarations
from anyblok.column import Decimal
from anyblok.column import Integer
from anyblok.relationship import Many2One
from anyblok.relationship import Many2Many

from anyblok_wms_base.exceptions import (
    OperationGoodsError,
    OperationMissingGoodsError,
    OperationMissingQuantityError,
    OperationQuantityError,
)

Mixin = Declarations.Mixin


@Declarations.register(Mixin)
class WmsSingleGoodsOperation:
    """Mixin for operations that apply to a single record of Goods."""

    goods = Many2One(model='Model.Wms.Goods', nullable=False)
    quantity = Decimal(label="Quantity")  # TODO non negativity constraint

    @classmethod
    def find_parent_operations(cls, goods=None, **kwargs):
        return [goods.reason]

    @classmethod
    def check_create_conditions(cls, state, goods=None, quantity=None,
                                **kwargs):
        if goods is None:
            raise OperationMissingGoodsError(
                cls,
                "The 'goods' keyword argument must be passed to the create() "
                "method")

        if quantity is None:
            raise OperationMissingQuantityError(
                cls,
                "The 'quantity keyword argument must be passed to "
                "the create() method")
        if state == 'done' and goods.state != 'present':
            raise OperationGoodsError(
                cls,
                "Can't create a Move in state 'done' for goods "
                "{goods} because of their state {goods.state}",
                goods=goods)

        if quantity > goods.quantity:
            raise OperationQuantityError(
                cls,
                "Can't move a greater quantity ({quantity}) than held in "
                "goods {goods} (which have quantity={goods.quantity})",
                quantity=quantity,
                goods=goods)

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


@Declarations.register(Declarations.Model.Wms.Operation)
class GoodsOriginalReason:
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
    acting_op = Many2One(model='Model.Wms.Operation',
                         index=True,
                         foreign_key_options={'ondelete': 'cascade'})
    reason = Many2One(model='Model.Wms.Operation',
                      foreign_key_options={'ondelete': 'cascade'})


@Declarations.register(Mixin)
class WmsMultipleGoodsOperation:
    """Mixin for operations that apply to a several records of Goods.

    We'll use a single table to represent the Many2Many relationship with
    Goods.
    """

    goods = Many2Many(model='Model.Wms.Goods',
                      join_table='join_wms_operation_multiple_goods',
                      m2m_remote_columns='goods_id',
                      m2m_local_columns='op_id',
                      label="Goods record to apply the operation to")

    @classmethod
    def find_parent_operations(cls, goods=None, **kwargs):
        return set(g.reason for g in goods)

    @classmethod
    def check_create_conditions(cls, state, goods=None, **kwargs):
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
        op = super(WmsMultipleGoodsOperation, cls).insert(**kwargs)
        op.goods.extend(goods)
        GOR = cls.registry.Wms.Operation.GoodsOriginalReason
        for record in goods:
            GOR.insert(goods=record,
                       acting_op=op,
                       reason=record.reason)
        return op

    def iter_goods_original_reasons(self):
        """List incoming goods together with their original reasons.

        Depending on the needs, it might be interesting to avoid
        actually fetching all those records.

        :return: a generator of pairs (goods, their original reasons)
        """
        GOR = self.registry.Wms.Operation.GoodsOriginalReason
        return ((gor.goods, gor.reason)
                for gor in GOR.query().filter(GOR.acting_op == self).all())

    def reset_goods_original_reasons(self, state=None):
        """Reset all input Goods to their original reason and state if passed.

        :param state: if not None, will be state on the input Goods

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
