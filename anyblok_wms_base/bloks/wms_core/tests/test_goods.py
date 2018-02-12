# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok.tests.testcase import BlokTestCase


class TestGoods(BlokTestCase):

    blok_entry_points = ('bloks', 'test_bloks')

    def setUp(self):
        Wms = self.registry.Wms

        self.Goods = Wms.Goods
        self.goods_type = self.Goods.Type.insert(label="My goods", code="MG")
        self.stock = Wms.Location.insert(label="Stock")
        self.arrival = Wms.Operation.Arrival.insert(
            goods_type=self.goods_type,
            location=self.stock,
            state='done',
            quantity=1)

    def test_prop_api(self):
        goods = self.Goods.insert(type=self.goods_type, quantity=1,
                                  reason=self.arrival, location=self.stock)

        self.assertIsNone(goods.get_property('foo'))
        self.assertEqual(goods.get_property('foo', default=-1), -1)

        goods.set_property('foo', 1)
        self.assertEqual(goods.get_property('foo'), 1)

    def test_prop_api_column(self):
        goods = self.Goods.insert(type=self.goods_type, quantity=1,
                                  reason=self.arrival, location=self.stock)

        goods.set_property('batch', '12345')
        self.assertEqual(goods.get_property('batch'), '12345')

    def test_prop_api_reserved(self):
        goods = self.Goods.insert(type=self.goods_type, quantity=1,
                                  reason=self.arrival, location=self.stock)

        with self.assertRaises(ValueError):
            goods.set_property('id', 1)
        with self.assertRaises(ValueError):
            goods.set_property('flexible', 'foo')

    def test_prop_api_internal(self):
        """Internal implementation details of Goods dict API.

        Separated to ease maintenance of tests in case it changes in
        the future.
        """
        goods = self.Goods.insert(type=self.goods_type, quantity=1,
                                  reason=self.arrival, location=self.stock)

        goods.set_property('foo', 2)
        self.assertEqual(goods.properties.flexible, dict(foo=2))

    def test_prop_api_column_internal(self):
        """Internal implementation details of Goods dict API (case of column)

        Separated to ease maintenance of tests in case it changes in
        the future.
        """
        goods = self.Goods.insert(type=self.goods_type, quantity=1,
                                  reason=self.arrival, location=self.stock)

        goods.set_property('batch', '2')
        self.assertEqual(goods.properties.flexible, {})
        self.assertEqual(goods.properties.batch, '2')
