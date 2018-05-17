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
    OperationError,
)

Mixin = Declarations.Mixin
Model = Declarations.Model
Wms = Model.Wms


@Declarations.register(Mixin)
class WmsSingleInputOperation:
    """Mixin for Operations that apply to a single record of Goods.

    This is synctactical sugar, allowing to work with such Operations as if
    Operations weren't meant in general for multiple inputs.
    """

    inputs_number = 1
    """Tell the base class that, indeed, we expect a single input."""

    @property
    def input(self):
        """Convenience attribute to refer to the single element of ``inputs``.
        """
        inps = self.inputs
        if not inps:  # can happen as an intermediate deletion step
            return '<unlinked>'
        return inps[0]

    @classmethod
    def create(cls, input=None, inputs=None, **kwargs):
        """Accept the alternative ``input`` arg and call back the base class.

        This override is for convenience in a case of a single input.
        """
        if input is not None and inputs is not None:
            # not an OperationInputsError, because it's not about the
            # contents of the inputs (one could say they aren't really known
            raise OperationError(
                cls,
                "You must choose between the 'input' and the 'inputs' "
                "kwargs (got input={input}, inputs={inputs}",
                input=input, inputs=inputs)
        if input is not None:
            inputs = (input, )
        return super(WmsSingleInputOperation, cls).create(
            inputs=inputs, **kwargs)

    def specific_repr(self):
        return "input={self.input!r}".format(self=self)
