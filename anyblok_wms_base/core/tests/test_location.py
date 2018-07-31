# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from sqlalchemy import or_
from anyblok_wms_base.constants import DATE_TIME_INFINITY
from anyblok_wms_base.testing import WmsTestCase


class TestLocation(WmsTestCase):

    blok_entry_points = ('bloks', 'test_bloks')

    def setUp(self):
        super(TestLocation, self).setUp()
        self.Avatar = self.Goods.Avatar
        self.goods_type = self.Goods.Type.insert(label="My goods",
                                                 code='MyGT')

        self.location_type = self.Goods.Type.insert(code="LOC")
        self.stock = self.insert_location('STK')

        self.arrival = self.Operation.Arrival.insert(
            goods_type=self.goods_type,
            location=self.stock,
            dt_execution=self.dt_test1,
            state='done')

        self.default_quantity_location = self.stock

    def insert_location(self, code, parent=None, tag=None, **fields):
        loc = self.Goods.insert(type=self.location_type,
                                code=code,
                                container_tag=tag,
                                **fields)
        if parent is not None:
            self.Goods.Avatar.insert(goods=loc,
                                     state='present',
                                     location=parent,
                                     dt_from=self.dt_test1,
                                     reason=self.arrival,  # purely formal
                                     dt_until=None)
        return loc

    def insert_goods(self, qty, state, dt_from, until=None, location=None):
        for _ in range(qty):
            self.Avatar.insert(
                goods=self.Goods.insert(type=self.goods_type),
                reason=self.arrival,
                location=self.stock if location is None else location,
                dt_from=dt_from,
                dt_until=until,
                state=state)

    def test_quantity(self):
        self.insert_goods(2, 'present', self.dt_test1)
        self.insert_goods(1, 'present', self.dt_test2)
        self.insert_goods(4, 'future', self.dt_test3)
        self.insert_goods(2, 'past', self.dt_test1, until=self.dt_test2)

        self.assert_quantity(3)
        self.assert_quantity(7, additional_states=['future'],
                             at_datetime=self.dt_test3)

        self.assert_quantity(3, additional_states=['future'],
                             at_datetime=self.dt_test2)
        # the 'past' and 'present' ones were already there
        self.assert_quantity(4, additional_states=['past'],
                             at_datetime=self.dt_test1)
        # the 'past' one was not there anymore,
        # but the two 'present' ones had already arrived
        self.assert_quantity(3, additional_states=['past'],
                             at_datetime=self.dt_test2)

    def test_quantity_at_infinity(self):
        self.insert_goods(2, 'present', self.dt_test1, until=self.dt_test2)
        self.insert_goods(1, 'present', self.dt_test2)
        self.insert_goods(3, 'future', self.dt_test2, until=self.dt_test3)
        self.insert_goods(4, 'future', self.dt_test3)
        self.insert_goods(2, 'past', self.dt_test1, until=self.dt_test2)

        self.assert_quantity(1, at_datetime=DATE_TIME_INFINITY)
        self.assert_quantity(5, additional_states=['future'],
                             at_datetime=DATE_TIME_INFINITY)

    def test_no_match(self):
        """Test that quantity is not None if no Goods match the criteria."""
        self.assert_quantity(0)

    def test_at_datetime_required(self):
        with self.assertRaises(ValueError):
            self.assert_quantity(0, additional_states=['past'])
        with self.assertRaises(ValueError):
            self.assert_quantity(0, additional_states=['future'])

    def test_tag_recursion(self):
        Goods = self.Goods
        self.stock.container_tag = 'sellable'
        stock_q = self.insert_location('STK/Q', parent=self.stock, tag='qa')
        stock_2 = self.insert_location('STK/2', parent=self.stock)

        stock_q1 = self.insert_location('STK/Q1', parent=stock_q)
        stock_qok = self.insert_location('STK/QOK', parent=stock_q,
                                         tag='sellable')

        cte = Goods.flatten_subquery_with_tags(top=self.stock)
        self.assertEqual(
            set(self.registry.session.query(cte.c.id, cte.c.tag).all()),
            {(self.stock.id, 'sellable'),
             (stock_q.id, 'qa'),
             (stock_2.id, 'sellable'),
             (stock_q1.id, 'qa'),
             (stock_qok.id, 'sellable'),
             })

        # example with no 'top', also demonstrating how to join (in this
        # case against on Location, to get full instances
        other = self.insert_location('foo', tag='bar')
        notag = self.insert_location('notag')
        cte = Goods.flatten_subquery_with_tags()
        joined = Goods.query(
            Goods, cte.c.tag).join(cte, cte.c.id == Goods.id)
        notsellable = set(joined.filter(cte.c.tag != 'sellable').all())
        self.assertEqual(notsellable,
                         {(stock_q, 'qa'),
                          (stock_q1, 'qa'),
                          (other, 'bar'),
                          })
        # notag wasn't there because of NULL semantics, and this has nothing
        # to do with the recursive CTE itself:
        self.assertEqual(joined.filter(cte.c.tag.is_(None)).one(),
                         (notag, None))

    def test_override_tag_recursion(self):
        Goods = self.Goods
        orig_meth = Goods.flatten_subquery_with_tags

        @classmethod
        def flatten_subquery_with_tags(cls, top=None, resolve_top_tag=True):
            """This is an example of flattening by code prefixing.

            Tag defaulting is disabled: only the direct tag is returned.
            Not specifying ``top`` is not supported
            """
            prefix = top.code + '/'
            query = Goods.query(
                Goods.id, Goods.container_tag.label('tag')).filter(or_(
                    Goods.code.like(prefix + '%'),
                    Goods.code == top.code))
            return query.subquery()

        other = self.insert_location('other')
        self.insert_goods(2, 'present', self.dt_test1)
        self.insert_goods(1, 'present', self.dt_test1, location=other)

        sub = self.insert_location('STK/sub', tag='foo')
        self.insert_goods(3, 'present', self.dt_test1, location=sub)

        try:
            Goods.flatten_subquery_with_tags = flatten_subquery_with_tags
            self.assert_quantity(5)
            self.assert_quantity(3, location_tag='foo')
        finally:
            Goods.flatten_subquery_with_tags = orig_meth

    def test_resolve_tag(self):
        sub = self.insert_location('sub', parent=self.stock)
        sub2 = self.insert_location('sub2', parent=sub)
        self.assertIsNone(self.stock.resolve_tag())
        self.assertIsNone(sub.resolve_tag())

        self.stock.container_tag = 'top'
        self.assertEqual(sub.resolve_tag(), 'top')
        self.assertEqual(sub2.resolve_tag(), 'top')

    def test_quantity_recursive(self):
        other = self.insert_location('other')
        self.insert_goods(2, 'present', self.dt_test1)
        self.insert_goods(1, 'present', self.dt_test1, location=other)

        sub = self.insert_location('sub', parent=self.stock, tag='foo')
        self.insert_goods(3, 'present', self.dt_test1, location=sub)

        self.assert_quantity(5)

        # this excludes sub, which has a tag
        self.assert_quantity(2, location_tag=None)

        self.assert_quantity(3, location_tag='foo')

        self.stock.container_tag = 'foo'
        self.assert_quantity(5, location_tag='foo')

    def test_quantity_recursive_top_tag_none(self):
        """Tag filtering works even if topmost location has no direct tag.
        """
        self.stock.container_tag = 'sell'
        sub = self.insert_location('sub', parent=self.stock)
        sub2 = self.insert_location('sub2', parent=sub)

        self.insert_goods(3, 'present', self.dt_test1)
        self.insert_goods(1, 'present', self.dt_test1, location=sub)
        self.insert_goods(2, 'present', self.dt_test1, location=sub2)
        # in a previous version, the recursion would have started with sub's
        # tag being None and propagate that to sub2. Now it doesn't
        self.assert_quantity(3, location=sub, location_tag='sell')
        self.assert_quantity(6)

    def test_quantity_tag_non_recursive(self):
        # normally it'd be redundant to ask for tag quantity for
        # non recursive queries, but for consistence it should work
        # (can happen as a result of some refactor, for instance, or
        # if upstream inputs are dynamic enough)

        self.insert_goods(2, 'present', self.dt_test1)
        self.assert_quantity(2, location_tag=None, location_recurse=False)
        self.assert_quantity(0, location_tag='foo', location_recurse=False)
        self.stock.container_tag = 'foo'
        self.assert_quantity(2, location_tag='foo', location_recurse=False)

    def test_quantity_tag_non_recursive_inherited(self):
        # still works if the tag is actually inherited
        sub = self.insert_location('sub', parent=self.stock)
        self.stock.container_tag = 'foo'
        self.insert_goods(2, 'present', self.dt_test1, location=sub)
        self.assert_quantity(2,
                             location=sub,
                             location_tag='foo',
                             location_recurse=False)
