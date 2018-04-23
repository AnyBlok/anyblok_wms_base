# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCase
from decimal import Decimal as D


class TestLocation(WmsTestCase):

    blok_entry_points = ('bloks', 'test_bloks')

    def setUp(self):
        super(TestLocation, self).setUp()
        Wms = self.registry.Wms

        self.Goods = Wms.Goods
        self.Avatar = Wms.Goods.Avatar
        self.goods_type = self.Goods.Type.insert(label="My goods")
        self.stock = Wms.Location.insert(label="Stock", code='STK')
        self.arrival = Wms.Operation.Arrival.insert(
            goods_type=self.goods_type,
            location=self.stock,
            dt_execution=self.dt_test1,
            state='done',
            quantity=5)

    def insert_goods(self, qty, state, dt_from, until=None):
        self.Avatar.insert(
            goods=self.Goods.insert(type=self.goods_type, quantity=qty),
            reason=self.arrival, location=self.stock,
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
        self.insert_goods(1, 'present', self.dt_test1)
        self.insert_goods(0.5, 'present', self.dt_test2)
        self.insert_goods(2, 'future', self.dt_test3)
        self.insert_goods(1, 'past', self.dt_test1, until=self.dt_test2)

        self.assertQuantity(D('1.5'))
        self.assertQuantity(D('3.5'), additional_states=['future'],
                            at_datetime=self.dt_test3)

        self.assertQuantity(D('1.5'), additional_states=['future'],
                            at_datetime=self.dt_test2)
        # the 'past' and 'present' ones were already there
        self.assertQuantity(2, additional_states=['past'],
                            at_datetime=self.dt_test1)
        # the 'past' one was not there anymore,
        # but the two 'present' ones had already arrived
        self.assertQuantity(1.5, additional_states=['past'],
                            at_datetime=self.dt_test2)

    def test_no_match(self):
        """Test that quantity is not None if no Goods match the criteria."""
        self.assertQuantity(0)

    def test_at_datetime_required(self):
        with self.assertRaises(ValueError):
            self.assertQuantity(0, additional_states=['past'])
        with self.assertRaises(ValueError):
            self.assertQuantity(0, additional_states=['future'])
