# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok.tests.testcase import BlokTestCase


class TestArrival(BlokTestCase):

    def setUp(self):
        Wms = self.registry.Wms
        self.goods_type = Wms.Goods.Type.insert(label="My good type")
        self.incoming_loc = Wms.Location.insert(label="Incoming location")
        self.stock = Wms.Location.insert(label="Stock")
        self.Arrival = Wms.Operation.Arrival
        self.Goods = Wms.Goods

    def test_create_planned_execute(self):
        arrival = self.Arrival.create(location=self.incoming_loc,
                                      quantity=3,
                                      state='planned',
                                      goods_type=self.goods_type)
        self.assertEqual(arrival.follows, [])
        arrived = self.Goods.query().filter(self.Goods.reason == arrival).all()
        self.assertEqual(len(arrived), 1)
        goods = arrived[0]
        self.assertEqual(goods.state, 'future')
        self.assertEqual(goods.location, self.incoming_loc)
        self.assertEqual(goods.quantity, 3)
        self.assertEqual(goods.type, self.goods_type)

        arrival.execute()
        self.assertEqual(goods.state, 'present')
        self.assertEqual(arrival.state, 'done')

    def test_create_done(self):
        arrival = self.Arrival.create(location=self.incoming_loc,
                                      quantity=3,
                                      state='done',
                                      goods_type=self.goods_type)
        self.assertEqual(arrival.follows, [])
        arrived = self.Goods.query().filter(self.Goods.reason == arrival).all()
        self.assertEqual(len(arrived), 1)
        goods = arrived[0]
        self.assertEqual(goods.state, 'present')
        self.assertEqual(goods.location, self.incoming_loc)
        self.assertEqual(goods.quantity, 3)
        self.assertEqual(goods.type, self.goods_type)
