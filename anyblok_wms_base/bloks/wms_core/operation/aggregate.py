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
    OperationGoodsError,
)

register = Declarations.register
Operation = Declarations.Model.Wms.Operation
MultipleGoods = Declarations.Mixin.WmsMultipleGoodsOperation

UNIFORM_FIELDS = ('type', 'properties', 'code', 'location')


@register(Operation)
class Aggregate(MultipleGoods, Operation):
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

    For the time being, a planned Aggregate creates two records in 'future'
    state:

    - the first has a positive quantity and is the one that will persist once
      the Aggregate will be executed
    - the second has a negative quantity being the exact negative of the
      first, so that the operation doesn't skew future stock levels.

    This is good enough for now, if not entirely satisfactory. Once we have
    visibility time ranges on moves, we might change this and enforce that
    all Goods records have positive quantities.

    TODO for the time being, the result of an Aggregate is a new record of
    Goods, it might be interesting to precise a target among self.goods,
    so that reversing a Split can actually become a no-op,
    restoring the original split Goods record to its initial state (perhaps
    excluding cases where Split is physical).
    """
    TYPE = 'wms_aggregate'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))

    def specific_repr(self):
        return "goods={self.goods!r}, ".format(self=self)

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
    def check_create_conditions(cls, state, goods=None, **kwargs):
        super(Aggregate, cls).check_create_conditions(
            state, goods=goods, **kwargs)
        first = goods[0]
        for record in goods:
            for field in UNIFORM_FIELDS:
                if not cls.field_is_equal(field, first, record):
                    raise OperationGoodsError(
                        cls,
                        "Can't create for goods {goods} "
                        "because of discrepancy in field {field!r}: "
                        "The record with id {first.id} has {first_field!r} "
                        "The record with id {second.id} has {second_field!r} ",
                        goods=goods, field=field,
                        first=first, first_field=getattr(first, field),
                        second=record, second_field=getattr(record, field))

    def after_insert(self):
        """Business logic after the inert insertion
        """
        self.registry.flush()
        goods = self.goods
        Goods = self.registry.Wms.Goods
        new_goods = {field: getattr(goods[0], field)
                     for field in UNIFORM_FIELDS}
        new_goods['reason'] = self
        qty = sum(record.quantity for record in goods)
        if self.state == 'done':
            for record in goods:
                record.update(reason=self, state='past')  # TODO dates
            return Goods.insert(state='present', quantity=qty, **new_goods)
        else:
            new_goods['state'] = 'future'
            Goods.insert(quantity=qty, **new_goods)
            Goods.insert(quantity=-qty, **new_goods)

    def execute_planned(self):
        Goods = self.registry.Wms.Goods
        query = Goods.query().filter(Goods.reason == self)
        query.filter(Goods.quantity < 0).delete(synchronize_session='fetch')
        created = query.filter(Goods.quantity > 0).one()
        created.state = 'present'
        for record in self.goods:
            record.update(state='past', reason=self)

    def cancel_single(self):
        Goods = self.registry.Wms.Goods
        Goods.query().filter(Goods.reason == self).delete(
            synchronize_session='fetch')
