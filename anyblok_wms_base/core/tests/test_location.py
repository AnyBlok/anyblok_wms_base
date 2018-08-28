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

        self.stock = self.insert_location('STK')

        self.arrival = self.Operation.Arrival.insert(
            goods_type=self.goods_type,
            location=self.stock,
            dt_execution=self.dt_test1,
            state='done')

        self.default_quantity_location = self.stock

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

    def test_recursion(self):
        """Test flatten_containers_subquery recursion, demonstrating joins.
        """
        Goods = self.Goods
        sell_loc_type = self.location_type
        nosell_loc_type = self.Wms.Goods.Type.insert(
            code='NOSELL',
            behaviours=dict(container={}))
        stock_q = self.insert_location('STK/Q', parent=self.stock,
                                       location_type=nosell_loc_type)
        stock_2 = self.insert_location('STK/2', parent=self.stock)

        stock_q1 = self.insert_location('STK/Q1', parent=stock_q,
                                        location_type=nosell_loc_type)
        stock_qok = self.insert_location('STK/QOK', parent=stock_q)

        cte = Goods.flatten_containers_subquery(top=self.stock)
        self.assertEqual(
            set(r[0] for r in self.registry.session.query(cte.c.id).all()),
            {self.stock.id, stock_q.id, stock_2.id, stock_q1.id, stock_qok.id}
        )

        # example with no 'top', also demonstrating how to join (in this
        # case against on Location, to get full instances
        other = self.insert_location('foo',
                                     location_type=self.Wms.Goods.Type.insert(
                                         code='NOSELL-OTHER',
                                         behaviours=dict(container={}))
                                     )
        cte = Goods.flatten_containers_subquery()
        joined = Goods.query().join(cte, cte.c.id == Goods.id)

        notsellable = set(joined.filter(Goods.type != sell_loc_type).all())
        self.assertEqual(notsellable, {stock_q, stock_q1, other})

        # Note that in this form, i.e. without joining on Avatars pointing to
        # the containers, there is nothing that actually restricts the
        # subquery to actually containers.
        self.insert_goods(1, 'present', self.dt_test1)
        self.assertIsNotNone(joined.filter(
            Goods.type == self.goods_type).first())

    def test_override_recursion(self):
        Goods = self.Goods
        orig_meth = Goods.flatten_containers_subquery

        @classmethod
        def flatten_containers_subquery(cls, top=None, **kwargs):
            """This is an example of flattening by code prefixing.

            Not specifying ``top`` is not supported in this simple example

            We also assume that locations don't move, and therefore ignore
            the at_datetime and additional_states kwargs
            """
            prefix = top.code + '/'
            query = Goods.query(Goods.id).filter(
                or_(
                    Goods.code.like(prefix + '%'),
                    Goods.code == top.code))
            return query.subquery()

        other = self.insert_location('other')
        self.insert_goods(2, 'present', self.dt_test1)
        self.insert_goods(1, 'present', self.dt_test1, location=other)

        sub = self.insert_location('STK/sub')
        self.insert_goods(3, 'present', self.dt_test1, location=sub)

        try:
            Goods.flatten_containers_subquery = flatten_containers_subquery
            self.assert_quantity(5)
        finally:
            Goods.flatten_containers_subquery = orig_meth

    def test_quantity_recursive(self):
        other = self.insert_location('other')
        self.insert_goods(2, 'present', self.dt_test1)
        self.insert_goods(1, 'present', self.dt_test1, location=other)

        sub = self.insert_location('sub', parent=self.stock)
        self.insert_goods(3, 'present', self.dt_test1, location=sub)

        self.assert_quantity(5)

    def test_create_root_container_wrong_type(self):
        with self.assertRaises(ValueError):
            self.Wms.create_root_container(self.goods_type)
