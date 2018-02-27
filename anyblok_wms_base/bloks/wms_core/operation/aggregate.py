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

    Aggregates replace some records of Goods at the same location,
    sharing equal properties with a single one bearing the total quantity.

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
    UNIFORM_FIELDS = ('type', 'properties', 'code', 'location')

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
        """Check that the Goods to aggregate are indeed indistinguishable.

        This performs the check from superclasses, and then compares all
        fields from :attr:`UNIFORM_FIELDS` in the specified ``goods``.
        """
        super(Aggregate, cls).check_create_conditions(
            state, dt_execution, inputs=inputs, **kwargs)
        first = inputs[0]
        for record in inputs:
            for field in cls.UNIFORM_FIELDS:
                if not cls.field_is_equal(field, first, record):
                    raise OperationInputsError(
                        cls,
                        "Can't create for goods {goods} "
                        "because of discrepancy in field {field!r}: "
                        "The record with id {first.id} has {first_field!r} "
                        "The record with id {second.id} has {second_field!r} ",
                        goods=inputs, field=field,
                        first=first, first_field=getattr(first, field),
                        second=record, second_field=getattr(record, field))

    def after_insert(self):
        """Business logic after the inert insertion
        """
        self.registry.flush()
        inputs = self.inputs
        dt_exec = self.dt_execution
        Goods = self.registry.Wms.Goods

        if self.state == 'done':
            update = dict(dt_until=dt_exec, state='past', reason=self)
        else:
            update = dict(dt_until=dt_exec)
        for record in inputs:
            record.update(**update)

        uniform_fields = {field: getattr(inputs[0], field)
                          for field in self.UNIFORM_FIELDS}
        return Goods.insert(
            reason=self,
            dt_from=dt_exec,
            # dt_until in states 'present' and 'future' is theoretical anyway
            dt_until=min_upper_bounds(g.dt_until for g in inputs),
            state='present' if self.state == 'done' else 'future',
            quantity=sum(g.quantity for g in inputs),
            **uniform_fields)

    def execute_planned(self):
        Goods = self.registry.Wms.Goods
        created = Goods.query().filter(Goods.reason == self).one()
        created.update(state='present', dt_from=self.dt_execution)
        for record in self.inputs:
            record.update(state='past', reason=self, dt_until=self.dt_execution)

    def cancel_single(self):
        Goods = self.registry.Wms.Goods
        Goods.query().filter(Goods.reason == self).delete(
            synchronize_session='fetch')

    def obliviate_single(self):
        self.reset_inputs_original_values(state='present')
        self.registry.flush()
        Goods = self.registry.Wms.Goods
        Goods.query().filter(Goods.reason == self).delete(
            synchronize_session='fetch')

    def is_reversible(self):
        """Reversibility depends on the relevant Goods Type.

        See :class:`Operation` for what reversibility exactly means in that
        context.
        """
        # that all Good Types are equal is part of pre-creation checks
        return self.inputs[0].type.is_aggregate_reversible()
