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

    def test_str(self):
        gt = self.goods_type
        goods = self.Goods.insert(type=gt, quantity=1,
                                  state='future',
                                  reason=self.arrival, location=self.stock)
        self.assertEqual(repr(goods),
                         "Wms.Goods(id=%d, state='future', type="
                         "Wms.Goods.Type(id=%d, code='MG'))" % (
                             goods.id, gt.id))
        self.assertEqual(str(goods),
                         "(id=%d, state='future', type="
                         "(id=%d, code='MG'))" % (goods.id, gt.id))

    def test_prop_api_column(self):
        goods = self.Goods.insert(type=self.goods_type, quantity=1,
                                  reason=self.arrival, location=self.stock)

        goods.set_property('batch', '12345')
        self.assertEqual(goods.get_property('batch'), '12345')

    def test_prop_api_duplication(self):
        goods = self.Goods.insert(type=self.goods_type, quantity=1,
                                  reason=self.arrival, location=self.stock)

        goods.set_property('batch', '12345')
        self.assertEqual(goods.get_property('batch'), '12345')

        goods2 = self.Goods.insert(type=self.goods_type, quantity=3,
                                   reason=self.arrival, location=self.stock,
                                   properties=goods.properties)
        goods2.set_property('batch', '6789')
        self.assertEqual(goods.get_property('batch'), '12345')
        self.assertEqual(goods2.get_property('batch'), '6789')

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


class TestGoodsProperties(BlokTestCase):

    def setUp(self):
        self.Props = self.registry.Wms.Goods.Properties

    def test_create(self):
        props = self.Props.create(batch='abcd',
                                  serial=1234, expiry='2018-03-01')
        self.assertEqual(props.to_dict(),
                         dict(batch='abcd',
                              id=props.id,
                              flexible=dict(serial=1234, expiry='2018-03-01')))
