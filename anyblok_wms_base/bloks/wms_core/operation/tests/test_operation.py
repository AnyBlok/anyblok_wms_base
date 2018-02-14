# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok.tests.testcase import BlokTestCase


class TestOperation(BlokTestCase):

    def setUp(self):
        Wms = self.registry.Wms
        self.Operation = Wms.Operation
        self.Goods = Wms.Goods
        self.incoming_loc = Wms.Location.insert(label="Incoming location")
        self.stock = Wms.Location.insert(label="Stock")
        self.goods_type = self.Goods.Type.insert(label="My good type")

    def test_history(self):
        arrival = self.Operation.Arrival.insert(goods_type=self.goods_type,
                                                location=self.incoming_loc,
                                                state='planned',
                                                quantity=3)

        goods = self.Goods.insert(quantity=3,
                                  type=self.goods_type,
                                  location=self.incoming_loc,
                                  state='future',
                                  reason=arrival)
        move = self.Operation.Move.insert(destination=self.stock,
                                          quantity=2,
                                          state='planned',
                                          goods=goods)
        move.follows.append(arrival)
        self.assertEqual(move.follows, [arrival])
        self.assertEqual(arrival.followers, [move])

    def test_cancel(self):
        arrival = self.Operation.Arrival.create(goods_type=self.goods_type,
                                                location=self.incoming_loc,
                                                state='planned',
                                                quantity=2)
        self.assertEqual(self.Goods.query().filter(
            self.Goods.state == 'future').count(), 1)

        arrival.cancel()
        self.assertEqual(self.Goods.query().filter(
            self.Goods.state == 'future').count(), 0)
        self.assertEqual(self.Operation.Arrival.query().count(), 0)

    def test_cancel_recursion(self):
        arrival = self.Operation.Arrival.create(goods_type=self.goods_type,
                                                location=self.incoming_loc,
                                                state='planned',
                                                quantity=3)
        goods = self.Goods.query().filter(self.Goods.reason == arrival).one()
        Move = self.Operation.Move
        Move.create(goods=goods,
                    quantity=1,
                    destination=self.stock,
                    state='planned')
        move2 = Move.create(goods=goods,
                            quantity=2,
                            destination=self.stock,
                            state='planned')
        goods2 = self.Goods.query().filter(self.Goods.reason == move2).one()
        self.Operation.Departure.create(goods=goods2,
                                        state='planned',
                                        quantity=2)
        arrival.cancel()
        self.assertEqual(self.Goods.query().filter(
            self.Goods.state == 'future').count(), 0)
        self.assertEqual(self.Operation.query().count(), 0)
