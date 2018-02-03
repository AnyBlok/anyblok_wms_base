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

    def setUp(self):
        Wms = self.registry.Wms

        self.Goods = Wms.Goods
        self.goods_type = self.Goods.Type.insert(label="My goods")
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

        goods.set_property('foo', 1)
        self.assertEqual(goods.get_property('foo'), 1)

    def test_prop_api_internal(self):
        """Internal implementation details of Goods dict API.

        Separated to ease maintenance of tests in case it changes in
        the future.
        """
        goods = self.Goods.insert(type=self.goods_type, quantity=1,
                                  reason=self.arrival, location=self.stock)

        goods.set_property('foo', 2)
        self.assertEqual(goods.properties.flexible, dict(foo=2))
