# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok.tests.testcase import BlokTestCase


class TestMove(BlokTestCase):

    def setUp(self):
        Wms = self.registry.Wms
        Operation = Wms.Operation
        goods_type = Wms.Goods.Type.insert(label="My good type")
        self.incoming_loc = Wms.Location.insert(label="Incoming location")
        self.stock = Wms.Location.insert(label="Stock")

        self.arrival = Operation.Arrival.insert(goods_type=goods_type,
                                                location=self.incoming_loc,
                                                state='planned',
                                                quantity=3)

        self.goods = Wms.Goods.insert(quantity=3,
                                      type=goods_type,
                                      location=self.incoming_loc,
                                      state='future',
                                      reason=self.arrival)
        self.Move = Operation.Move
        self.Goods = Wms.Goods

    def test_whole_planned_execute(self):
        move = self.Move.create(destination=self.stock,
                                quantity=3,
                                state='planned',
                                goods=self.goods)
        self.assertEqual(move.follows, [self.arrival])
        self.assertEqual(move.goods, self.goods)
        self.goods.update(state='present')

        move.execute()
        self.assertEqual(move.state, 'done')
        moved = self.Goods.query().filter(self.Goods.reason == move).all()
        self.assertEqual(len(moved), 1)
        moved = moved[0]
        self.assertEqual(moved.state, 'present')
        self.assertEqual(moved.reason, move)
        self.assertEqual(self.Goods.query().filter(
            self.Goods.location == self.incoming_loc).count(), 0)

    def test_whole_planned_execute_but_not_ready(self):
        move = self.Move.create(destination=self.stock,
                                quantity=3,
                                state='planned',
                                goods=self.goods)
        self.assertEqual(move.follows, [self.arrival])
        self.assertEqual(move.goods, self.goods)
        with self.assertRaises(ValueError):
            move.execute()

    def test_whole_done(self):
        self.goods.update(state='present')
        move = self.Move.create(destination=self.stock,
                                quantity=3,
                                state='done',
                                goods=self.goods)
        self.assertEqual(move.follows, [self.arrival])

    def test_whole_done_but_not_ready(self):
        with self.assertRaises(ValueError):
            self.Move.create(destination=self.stock,
                             quantity=3,
                             state='done',
                             goods=self.goods)
