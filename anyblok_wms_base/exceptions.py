# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
"""All exceptions for anyblok_wms_base bloks."""


class OperationError(ValueError):

    operation = None
    """``None`` if raised for a Model class, Operation instance otherwise"""

    def __init__(self, model_or_record, fmt, **kwargs):
        self.fmt = fmt
        self.model_name = model_or_record.__registry_name__
        if not isinstance(model_or_record, type):
            kwargs['operation'] = self.operation = model_or_record
        self.kwargs = kwargs

    def __repr__(self):
        formatted_kwargs = ', '.join(
            '%s=%r' % (k, v) for k, v in self.kwargs.items())
        return self.__class__.__name__ + '(%s, %r, %s)' % (
            self.model_name, self.fmt, formatted_kwargs)

    def __str__(self):
        return self.model_name + ': ' + self.fmt.format(**self.kwargs)


class OperationInputsError(OperationError):
    """Used in Operations for errors about their inputs.

    classmethods, such as :meth:`create
    <anyblok_wms_base.bloks.wms_core.operation.base.Operation.create>`
    must pass the ``inputs`` kwarg.
    """

    def __init__(self, model_or_record, fmt, **kwargs):
        OperationError.__init__(self, model_or_record, fmt, **kwargs)
        op = self.operation
        if op is None:
            if 'inputs' not in kwargs:
                raise ValueError("OperationInputsError for classmethods must "
                                 "pass the 'inputs' kwarg")
        else:
            self.kwargs['inputs'] = self.operation.inputs


class OperationInputWrongState(OperationInputsError):

    def __init__(self, op_model_or_record, record, expected_state,
                 prelude=None, fmt=None, **kwargs):
        if fmt is None:
            if prelude is None:
                prelude = "Error for {operation}"
            fmt = prelude + (" because at least one of the inputs "
                             "(id={record.id}) has state {record.state!r} "
                             "instead of the expected {expected_state!r}")
        OperationInputsError.__init__(
            self, op_model_or_record, fmt, record=record,
            expected_state=expected_state, **kwargs)


class OperationMissingInputsError(OperationInputsError):
    """Used in Operation creation if inputs aren't passed."""


class OperationQuantityError(OperationInputsError):
    """Used if an operation has an issue with some quantity."""

    def __init__(self, model_or_class, fmt,
                 input=None, op_quantity=None, **kwargs):
        if input is not None:
            kwargs['inputs'] = [input]
            kwargs['input'] = input

        super(OperationQuantityError, self).__init__(model_or_class, fmt,
                                                     op_quantity=op_quantity,
                                                     **kwargs)

        op = self.operation
        if op is not None:
            if op_quantity is None:
                self.kwargs['op_quantity'] = op.quantity
            if input is None:
                kwargs['input'] = op.input


class OperationMissingQuantityError(OperationError):
    """Used if the operation requires some quantity that's not passed."""


class OperationIrreversibleError(OperationError):
    """Raised if trying to revert an irreversible operation."""

    def __init__(self, op, **kw):
        OperationError.__init__(
            self, op, "this can depend on the Operation class or "
            "on the present instance: {op}", op=op)


class OperationGoodsReserved(OperationError):
    """Used if an Operation tries and work on some reserved Goods in a
    txn that doesn't own the reservation."""
