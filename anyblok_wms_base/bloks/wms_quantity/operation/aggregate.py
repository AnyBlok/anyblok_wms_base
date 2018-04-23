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

from anyblok_wms_base.utils import min_upper_bounds
from anyblok_wms_base.exceptions import (
    OperationInputsError,
)

register = Declarations.register
Operation = Declarations.Model.Wms.Operation


@register(Operation)
class Aggregate(Operation):
    """An aggregation of Goods record.

    Aggregate is the converse of Split.

    Like Splits, Aggregates are operations of a special kind,
    that have to be considered internal details of wms_core, and are not
    guaranteed to exist in the future.

    Aggregates replace some records of Goods
    sharing equal properties and type, with Avatars at the same location with
    a single one bearing the total quantity, and a new Avatar.

    While non trivial in the database, they may have no physical counterpart in
    the real world. We call them *formal* in that case.

    Formal Aggregate Operations can always be reverted with Splits,
    but only some physical Aggregate Operations can be reverted, depending on
    the Goods Type. See :class:`Model.Wms.Goods.Type` for a full discussion of
    this, with use cases.

    In the formal case, we've decided to represent this as an Operation
    for the sake of consistency, and especially to avoid too much special
    cases implementation of various Operations.
    The benefit is that they appear explicitely in the history.

    TODO implement :meth:`plan_revert_single`
    """
    TYPE = 'wms_aggregate'
    UNIFORM_GOODS_FIELDS = ('type', 'properties', 'code')
    UNIFORM_AVATAR_FIELDS = ('location', )

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
        fields from :attr:`UNIFROM_AVATAR_FIELDS` on the inputs (Avatars) and
        :attr:`UNIFORM_GOODS_FIELDS` (on the underlying Goods).
        """
        super(Aggregate, cls).check_create_conditions(
            state, dt_execution, inputs=inputs, **kwargs)
        first = inputs[0]
        first_goods = first.goods
        for avatar in inputs:
            goods = avatar.goods
            diff = {}  # field name -> (first value, second value)
            for field in cls.UNIFORM_GOODS_FIELDS:
                if not cls.field_is_equal(field, first_goods, goods):
                    diff[field] = (getattr(first_goods, field),
                                   getattr(goods, field))
            for field in cls.UNIFORM_AVATAR_FIELDS:
                first_value = getattr(first, field)
                second_value = getattr(avatar, field)
                if first_value != second_value:
                    diff[field] = (first_value, second_value)

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
        # TODO find a way to pass the actual wished Goods up to here, then
        # use it (to maintain Goods record in case of reverts)
        self.registry.flush()
        inputs = self.inputs
        dt_exec = self.dt_execution
        Goods = self.registry.Wms.Goods

        outcome_dt_until = min_upper_bounds(g.dt_until for g in inputs)

        if self.state == 'done':
            update = dict(dt_until=dt_exec, state='past', reason=self)
        else:
            update = dict(dt_until=dt_exec)
        for record in inputs:
            record.update(**update)

        tpl_avatar = inputs[0]
        tpl_goods = tpl_avatar.goods
        uniform_goods_fields = {field: getattr(tpl_goods, field)
                                for field in self.UNIFORM_GOODS_FIELDS}
        uniform_avatar_fields = {field: getattr(tpl_avatar, field)
                                 for field in self.UNIFORM_AVATAR_FIELDS}
        aggregated_goods = Goods.insert(
            quantity=sum(a.goods.quantity for a in inputs),
            **uniform_goods_fields)

        return Goods.Avatar.insert(
            goods=aggregated_goods,
            reason=self,
            dt_from=dt_exec,
            # dt_until in states 'present' and 'future' is theoretical anyway
            dt_until=outcome_dt_until,
            state='present' if self.state == 'done' else 'future',
            **uniform_avatar_fields)

    def execute_planned(self):
        self.outcomes[0].update(state='present', dt_from=self.dt_execution)
        for record in self.inputs:
            record.update(state='past', reason=self, dt_until=self.dt_execution)

    def is_reversible(self):
        """Reversibility depends on the relevant Goods Type.

        See :class:`Operation` for what reversibility exactly means in that
        context.
        """
        # that all Good Types are equal is part of pre-creation checks
        return self.inputs[0].goods.type.is_aggregate_reversible()
