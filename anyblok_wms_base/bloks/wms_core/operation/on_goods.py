# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
"""Mixins for Operations that take exactly on Goods record as input.
"""

from anyblok import Declarations

from anyblok_wms_base.exceptions import (
    OperationInputsError,
    OperationQuantityError,
)

Mixin = Declarations.Mixin
Model = Declarations.Model
Wms = Model.Wms


@Declarations.register(Mixin)
class WmsSingleInputOperation:
    """Mixin for operations that apply to a single record of Goods."""

    inputs_number = 1

    @property
    def input(self):
        return self.inputs[0]

    @input.setter
    def input(self, goods):
        self.link_inputs([goods], clear=True)

    def check_execute_conditions(self):
        super(WmsSingleInputOperation, self).check_execute_conditions()
        # TODO this should move to splitter, WmsSingleInputOperation
        # is not quantity-aware anymore
        goods = self.input
        if self.quantity > goods.quantity:
            raise OperationQuantityError(
                self,
                "Can't execute {op}, whose quantity {op.quantity} is greater "
                "than on its input {goods}, "
                "although it's been successfully planned.",
                op=self, goods=self.input)

    @classmethod
    def create(cls, input=None, inputs=None, **kwargs):
        if input is not None and inputs is not None:
            raise OperationInputsError(
                cls,
                "You must choose between the 'input' and the 'inputs' "
                "kwargs (got input={input}, inputs={inputs}",
                input=input, inputs=inputs)
        if input is not None:
            inputs = (input, )
        return super(WmsSingleInputOperation, cls).create(
            inputs=inputs, **kwargs)
