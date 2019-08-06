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

from anyblok_wms_base.exceptions import (
    OperationInputsError,
)

register = Declarations.register
Mixin = Declarations.Mixin
Operation = Declarations.Model.Wms.Operation


@register(Operation)
class Aggregate(Mixin.WmsSingleOutcomeOperation,
                Mixin.WmsInPlaceOperation,
                Operation):
    """An aggregation of PhysObj record.

    Aggregate is the converse of Split.

    Like Splits, Aggregates are operations of a special kind,
    that have to be considered internal details of wms_core, and are not
    guaranteed to exist in the future.

    Aggregates replace some records of PhysObj
    sharing equal properties and type, with Avatars at the same location with
    a single one bearing the total quantity, and a new Avatar.

    While non trivial in the database, they may have no physical counterpart in
    the real world. We call them *formal* in that case.

    Formal Aggregate Operations can always be reverted with Splits,
    but only some physical Aggregate Operations can be reverted, depending on
    the PhysObj Type. See :class:`Model.Wms.PhysObj.Type` for a full
    discussion of this, with use cases.

    In the formal case, we've decided to represent this as an Operation
    for the sake of consistency, and especially to avoid too much special
    cases implementation of various Operations.
    The benefit is that they appear explicitely in the history.

    TODO implement :meth:`plan_revert_single`
    """
    TYPE = 'wms_aggregate'
    UNIFORM_PHYSOBJ_FIELDS = ('type', 'properties', 'code')

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))

    def specific_repr(self):
        return "inputs={self.inputs!r}, ".format(self=self)

    @staticmethod
    def field_is_equal(field, goods_rec1, goods_rec2):
        """Return True if given field is equal in the two goods records.

        This is singled out because of properties, for which we don't want
        to assert equality of the properties lines, but of their content.

        TODO: see if implementing __eq__ etc for properties would be a
        bad idea (would it confuse the Anyblok or SQLAlchemy?)
        """
        val1, val2 = getattr(goods_rec1, field), getattr(goods_rec2, field)
        if field != 'properties' or val1 is None or val2 is None:
            return val1 == val2

        # TODO implement on Properties class and test separately
        # TODO PERF (minor): we could use fields_description() directly
        props1 = val1.to_dict()
        props2 = val2.to_dict()
        props1.pop('id')
        props2.pop('id')
        return props1 == props2

    @classmethod
    def check_create_conditions(cls, state, dt_execution, inputs=None,
                                **kwargs):
        """Check that the inputs to aggregate are indeed indistinguishable.

        This performs the check from superclasses, and then compares all
        fields from :attr:`UNIFORM_GOODS_FIELDS` (on the underlying PhysObj).
        """
        super(Aggregate, cls).check_create_conditions(
            state, dt_execution, inputs=inputs, **kwargs)
        first = inputs[0]
        first_physobj = first.obj
        for avatar in inputs:
            physobj = avatar.obj
            diff = {}  # field name -> (first value, second value)
            for field in cls.UNIFORM_PHYSOBJ_FIELDS:
                if not cls.field_is_equal(field, first_physobj, physobj):
                    diff[field] = (getattr(first_physobj, field),
                                   getattr(physobj, field))
            # consistency of the Avatars is just about Location
            # and that's checked by WmsInPlaceOperation
            if diff:
                raise OperationInputsError(
                    cls,
                    "Can't create Aggregate with inputs {inputs} "
                    "because of discrepancy in field {field!r}: "
                    "Here's a mapping giving by field the differing "
                    "values between the record with id {first.id} "
                    "and the one with id {second.id}: {diff!r} ",
                    inputs=inputs, field=field,
                    first=first, second=avatar, diff=diff)

    def after_insert(self):
        """Business logic after the inert insertion
        """
        # TODO find a way to pass the actual wished PhysObj up to here, then
        # use it (to maintain PhysObj record in case of reverts)
        self.registry.flush()
        inputs = self.inputs
        dt_exec = self.dt_execution
        PhysObj = self.registry.Wms.PhysObj

        if self.state == 'done':
            update = dict(dt_until=dt_exec, state='past')
        else:
            update = dict(dt_until=dt_exec)
        for record in inputs:
            record.update(**update)

        tpl_avatar = next(iter(inputs))
        tpl_physobj = tpl_avatar.obj
        uniform_physobj_fields = {field: getattr(tpl_physobj, field)
                                  for field in self.UNIFORM_PHYSOBJ_FIELDS}
        aggregated_physobj = PhysObj.insert(
            quantity=sum(a.obj.quantity for a in inputs),
            **uniform_physobj_fields)

        return PhysObj.Avatar.insert(
            obj=aggregated_physobj,
            outcome_of=self,
            dt_from=dt_exec,
            # dt_until in states 'present' and 'future' is theoretical anyway
            state='present' if self.state == 'done' else 'future',
            location=self.unique_inputs_location(inputs))

    def execute_planned(self):
        self.outcome.update(state='present', dt_from=self.dt_execution)
        for record in self.inputs:
            record.update(state='past',
                          dt_until=self.dt_execution)

    def is_reversible(self):
        """Reversibility depends on the relevant PhysObj Type.

        See :class:`Operation` for what reversibility exactly means in that
        context.
        """
        # that all Good Types are equal is part of pre-creation checks
        return self.inputs[0].obj.type.is_aggregate_reversible()
