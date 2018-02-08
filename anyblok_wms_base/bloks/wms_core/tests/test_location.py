# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok.tests.testcase import BlokTestCase
from decimal import Decimal as D


class TestGoods(BlokTestCase):

    blok_entry_points = ('bloks', 'test_bloks')

    def setUp(self):
        Wms = self.registry.Wms

        self.Goods = Wms.Goods
        self.goods_type = self.Goods.Type.insert(label="My goods")
        self.stock = Wms.Location.insert(label="Stock")
        self.arrival = Wms.Operation.Arrival.insert(
            goods_type=self.goods_type,
            location=self.stock,
            state='done',
            quantity=5)

    def insert_goods(self, qty, state):
        self.Goods.insert(type=self.goods_type, quantity=qty,
                          reason=self.arrival, location=self.stock,
                          state=state)

    def assertQuantity(self, quantity, **kwargs):
        self.assertEqual(
            self.stock.quantity(self.goods_type, **kwargs),
            quantity)

    def test_quantity(self):
        self.insert_goods(1, 'present')
        self.insert_goods(0.5, 'present')
        self.insert_goods(2, 'future')
        self.insert_goods(1, 'past')

        self.assertQuantity(D('1.5'))
        self.assertQuantity(D('1.5'), goods_state='present')
        self.assertQuantity(D('3.5'), goods_state='future')
        self.assertQuantity(1, goods_state='past')

    def test_no_match(self):
        """Test that quantity is not None if no Goods match the criteria."""
        self.assertQuantity(0)
