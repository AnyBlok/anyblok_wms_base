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


class OperationForbiddenState(OperationError):
    """Raised by Operations that forbid certain states.
    """

    def __init__(self, *args, **kwargs):
        if 'forbidden' not in kwargs:
            raise ValueError("OperationForbiddenState must pass the state "
                             "that has been refused as the 'forbidden' kwargs")

        OperationError.__init__(self, *args, **kwargs)


class OperationInputsError(OperationError):
    """Used in Operations for errors about their inputs.

    classmethods, such as :meth:`create
    <anyblok_wms_base.core.operation.base.Operation.create>`
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


class OperationContainerExpected(OperationError):
    """Raised by Operations involving containers / locations.

    If some Operation expects something to be container (also thought as a
    location) and it turns out not to be one, the Operation is supposed to
    raise this exception.
    """

    def __init__(self, op, msg, offender=None, **kw):
        fmt = msg + " was expected to be a container, but is not"
        OperationError.__init__(self, op, fmt, offender=offender)


class AssemblyInputNotMatched(OperationInputsError):

    def __init__(self, op_model_or_record, spec_item,
                 from_state=None, to_state=None,
                 prelude=None, fmt=None, **kwargs):
        """Initialisation.

        :param spec_item: the pair made of the item in inputs specification that
                          hasn't been matched and its index (first is 0).
        """
        spec_detail, spec_index = spec_item

        if fmt is None:
            if prelude is None:
                prelude = "In {operation}"
            fmt = prelude + (", could not satisfy inputs specification item "
                             "#{spec_nr} {spec_detail} "
                             "while going from state {from_state!r} "
                             "to {to_state!r} "
                             "(after previous items have been satisfied)")
        OperationInputsError.__init__(
            self, op_model_or_record, fmt,
            spec_index=spec_index,
            spec_nr=spec_index + 1,
            spec_detail=spec_detail,
            from_state=from_state,
            to_state=to_state,
            **kwargs)


class AssemblyPropertyConflict(OperationInputsError):

    def __init__(self, op, spec_item, prop, existing, candidate,
                 prelude=None, fmt=None, **kwargs):
        """Initialisation.

        :param spec_item: the pair made of the item in inputs specification that
                          hasn't been matched and its index (first is 0),
                          or None for conflicts arising from the global
                          ``forward_properties`` parameters.
        """
        fmt = "{operation}, inconsistent properties. "
        if spec_item is None:
            fmt += "In global Properties forwarding for extra inputs, "
            kwargs['global_extra'] = True
        else:
            kwargs['spec_index'], kwargs['spec_detail'] = spec_item
            kwargs['spec_nr'] = kwargs['spec_index'] + 1
            fmt += "Input specification item #{spec_nr} {spec_detail} "

        fmt += ("would override the already set value "
                "{existing!r} of Property {prop!r} "
                "with {candidate!r}")
        OperationInputsError.__init__(
            self, op, fmt,
            prop=prop,
            candidate=candidate,
            existing=existing,
            **kwargs)


class AssemblyWrongInputProperties(OperationInputsError):
    """For inputs properties been checked in Assembly.

    It can be raised either for global or per input requirements.
    In the latter case, the given input specification can be passed, taking
    form of the ``spec_idx``, ``spec_nr`` and ``spec_detail``
    kwargs, similarly to :class:`AssemblyInputNotMatched`.
    for global requirements, these  kwargs should be set to ``None``
    """
    def __init__(self, op, avatar, req_props, req_prop_values,
                 spec_item=None,
                 prelude=None, fmt=None, **kwargs):
        """Initialisation.

        :param req_props: the properties whose existence was required
        :param req_prop_values: the property values that were required
        """
        fmt = ("{operation}, wrong properties on {avatar!r}. "
               "The existence of {required_props!r} is required, and "
               "the following values are required: {required_prop_values!r}")
        if spec_item is None:
            spec_idx = spec_detail = spec_nr = None
        else:
            spec_idx, spec_detail = spec_item
            spec_nr = spec_idx + 1
            fmt += " due to input specification #{spec_nr} {spec_detail} "
        OperationInputsError.__init__(
            self, op, fmt,
            avatar=avatar,
            spec_idx=spec_idx,
            spec_detail=spec_detail,
            spec_nr=spec_nr,
            required_props=req_props,
            required_prop_values=req_prop_values,
            **kwargs)


class AssemblyExtraInputs(OperationInputsError):

    def __init__(self, op, extra,
                 prelude=None, fmt=None, **kwargs):
        """Initialisation.

        :param spec_item: the pair made of the item in inputs specification that
                          hasn't been matched and its index (first is 0).
        """
        if fmt is None:
            if prelude is None:
                prelude = "In {operation}"
            fmt = prelude + (", extra inputs {extra!r} after all required "
                             "ones have been found, but this is not allowed "
                             "in behaviour for Assembly {op_name!r}")
        OperationInputsError.__init__(self, op, fmt,
                                      op_name=op.name,
                                      extra=extra,
                                      **kwargs)


class UnknownExpressionType(OperationError):

    def __init__(self, op, etype, evalue,
                 prelude=None, fmt=None, **kwargs):
        """Initialisation.

        :param spec_item: the pair made of the item in inputs specification that
                          hasn't been matched and its index (first is 0).
        """
        if fmt is None:
            if prelude is None:
                prelude = "In {operation}"
            fmt = prelude + (", unknown expression type {expr_type} "
                             "(value was {expr_value})")
        OperationError.__init__(self, op, fmt,
                                expr_type=etype, expr_value=evalue)
