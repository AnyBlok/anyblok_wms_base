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
        Wms = self.registry.Wms

        self.Goods = Wms.Goods
        self.Avatar = Wms.Goods.Avatar
        self.goods_type = self.Goods.Type.insert(label="My goods",
                                                 code='MyGT')

        self.Location = Wms.Location
        self.stock = Wms.Location.insert(label="Stock", code='STK')
        self.arrival = Wms.Operation.Arrival.insert(
            goods_type=self.goods_type,
            location=self.stock,
            dt_execution=self.dt_test1,
            state='done')

    def insert_goods(self, qty, state, dt_from, until=None, location=None):
        for _ in range(qty):
            self.Avatar.insert(
                goods=self.Goods.insert(type=self.goods_type),
                reason=self.arrival,
                location=self.stock if location is None else location,
                dt_from=dt_from,
                dt_until=until,
                state=state)

    def test_str_repr(self):
        self.assertTrue('STK' in repr(self.stock))
        self.assertTrue('STK' in str(self.stock))

    def assertQuantity(self, quantity, **kwargs):
        self.assertEqual(
            self.stock.quantity(self.goods_type, **kwargs),
            quantity)

    def test_quantity(self):
        self.insert_goods(2, 'present', self.dt_test1)
        self.insert_goods(1, 'present', self.dt_test2)
        self.insert_goods(4, 'future', self.dt_test3)
        self.insert_goods(2, 'past', self.dt_test1, until=self.dt_test2)

        self.assertQuantity(3)
        self.assertQuantity(7, additional_states=['future'],
                            at_datetime=self.dt_test3)

        self.assertQuantity(3, additional_states=['future'],
                            at_datetime=self.dt_test2)
        # the 'past' and 'present' ones were already there
        self.assertQuantity(4, additional_states=['past'],
                            at_datetime=self.dt_test1)
        # the 'past' one was not there anymore,
        # but the two 'present' ones had already arrived
        self.assertQuantity(3, additional_states=['past'],
                            at_datetime=self.dt_test2)

    def test_quantity_at_infinity(self):
        self.insert_goods(2, 'present', self.dt_test1, until=self.dt_test2)
        self.insert_goods(1, 'present', self.dt_test2)
        self.insert_goods(3, 'future', self.dt_test2, until=self.dt_test3)
        self.insert_goods(4, 'future', self.dt_test3)
        self.insert_goods(2, 'past', self.dt_test1, until=self.dt_test2)

        self.assertQuantity(1, at_datetime=DATE_TIME_INFINITY)
        self.assertQuantity(5, additional_states=['future'],
                            at_datetime=DATE_TIME_INFINITY)

    def test_no_match(self):
        """Test that quantity is not None if no Goods match the criteria."""
        self.assertQuantity(0)

    def test_at_datetime_required(self):
        with self.assertRaises(ValueError):
            self.assertQuantity(0, additional_states=['past'])
        with self.assertRaises(ValueError):
            self.assertQuantity(0, additional_states=['future'])

    def test_tag_recursion(self):
        Location = self.Location
        self.stock.tag = 'sellable'
        stock_q = Location.insert(code='STK/Q', parent=self.stock, tag='qa')
        stock_2 = Location.insert(code='STK/2', parent=self.stock)

        stock_q1 = Location.insert(code='STK/Q1', parent=stock_q)
        stock_qok = Location.insert(code='STK/QOK', parent=stock_q,
                                    tag='sellable')

        cte = Location.flatten_subquery_with_tags(top=self.stock)
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
        other = Location.insert(code='foo', tag='bar')
        notag = Location.insert(code='notag')
        cte = Location.flatten_subquery_with_tags()
        joined = Location.query(
            Location, cte.c.tag).join(cte, cte.c.id == Location.id)
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
        Location = self.Location
        orig_meth = Location.flatten_subquery_with_tags

        @classmethod
        def flatten_subquery_with_tags(cls, top=None, resolve_top_tag=True):
            """This is an example of flattening by code prefixing.

            Tag defaulting is disabled: only the direct tag is returned.
            Not specifying ``top`` is not supported
            """
            prefix = top.code + '/'
            query = Location.query(Location.id, Location.tag).filter(or_(
                Location.code.like(prefix + '%'),
                Location.code == top.code))
            return query.subquery()

        other = self.Location.insert(code='other')
        self.insert_goods(2, 'present', self.dt_test1)
        self.insert_goods(1, 'present', self.dt_test1, location=other)

        sub = self.Location.insert(code='STK/sub', tag='foo')
        self.insert_goods(3, 'present', self.dt_test1, location=sub)

        try:
            Location.flatten_subquery_with_tags = flatten_subquery_with_tags
            self.assertQuantity(5)
            self.assertQuantity(3, location_tag='foo')
        finally:
            Location.flatten_subquery_with_tags = orig_meth

    def test_resolve_tag(self):
        sub = self.Location.insert(code='sub', parent=self.stock)
        sub2 = self.Location.insert(code='sub2', parent=sub)
        self.assertIsNone(self.stock.resolve_tag())
        self.assertIsNone(sub.resolve_tag())

        self.stock.tag = 'top'
        self.assertEqual(sub.resolve_tag(), 'top')
        self.assertEqual(sub2.resolve_tag(), 'top')

    def test_quantity_recursive(self):
        other = self.Location.insert(code='other')
        self.insert_goods(2, 'present', self.dt_test1)
        self.insert_goods(1, 'present', self.dt_test1, location=other)

        sub = self.Location.insert(code='sub', parent=self.stock, tag='foo')
        self.insert_goods(3, 'present', self.dt_test1, location=sub)

        self.assertQuantity(5)

        # this excludes sub, which has a tag
        self.assertQuantity(2, location_tag=None)

        self.assertQuantity(3, location_tag='foo')

        self.stock.tag = 'foo'
        self.assertQuantity(5, location_tag='foo')

    def test_quantity_recursive_top_tag_none(self):
        """Tag filtering works even if topmost location has no direct tag.
        """
        self.stock.tag = 'sell'
        sub = self.Location.insert(code='sub', parent=self.stock)
        sub2 = self.Location.insert(code='sub2', parent=sub)

        self.insert_goods(3, 'present', self.dt_test1)
        self.insert_goods(1, 'present', self.dt_test1, location=sub)
        self.insert_goods(2, 'present', self.dt_test1, location=sub2)
        # in a previous version, the recursion would have started with sub's
        # tag being None and propagate that to sub2. Now it doesn't
        self.assertEqual(sub.quantity(self.goods_type, location_tag='sell'),
                         3)
        self.assertQuantity(6)

    def test_quantity_tag_non_recursive(self):
        # normally it'd be redundant to ask for tag quantity for
        # non recursive queries, but for consistence it should work
        # (can happen as a result of some refactor, for instance, or
        # if upstream inputs are dynamic enough)

        self.insert_goods(2, 'present', self.dt_test1)
        self.assertQuantity(2, location_tag=None, recursive=False)
        self.assertQuantity(0, location_tag='foo', recursive=False)
        self.stock.tag = 'foo'
        self.assertQuantity(2, location_tag='foo', recursive=False)

    def test_quantity_tag_non_recursive_inherited(self):
        # still works if the tag is actually inherited
        sub = self.Location.insert(code='sub', parent=self.stock)
        self.stock.tag = 'foo'
        self.insert_goods(2, 'present', self.dt_test1, location=sub)
        self.assertEqual(sub.quantity(self.goods_type,
                                      recursive=False,
                                      location_tag='foo'),
                         2)
