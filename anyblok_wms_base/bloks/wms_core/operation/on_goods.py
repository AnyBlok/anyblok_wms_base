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

from anyblok_wms_base.exceptions import (
    OperationGoodsError,
    OperationQuantityError,
)

Mixin = Declarations.Mixin
Model = Declarations.Model
Wms = Model.Wms


@Declarations.register(Mixin)
class WmsSingleGoodsOperation:
    """Mixin for operations that apply to a single record of Goods."""

    working_on_number = 1

    @property
    def goods(self):
        return self.working_on[0]

    @goods.setter
    def goods(self, goods):
        self.link_working_on([goods], clear=True)

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

    @classmethod
    def create(cls, goods=None, working_on=None, **kwargs):
        if goods is not None and working_on is not None:
            raise OperationGoodsError(
                cls,
                "You must choose between the 'goods' and the 'working_on' "
                "kwargs (got goods={goods}, working_on={working_on}",
                goods=goods, working_on=working_on)
        if goods is not None:
            working_on = (goods, )
        return super(WmsSingleGoodsOperation, cls).create(
            working_on=working_on, **kwargs)
