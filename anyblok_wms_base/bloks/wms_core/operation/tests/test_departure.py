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
        self.goods_type = Wms.Goods.Type.insert(label="My good type")
        self.incoming_loc = Wms.Location.insert(label="Incoming location")
        self.stock = Wms.Location.insert(label="Stock")

        self.arrival = Operation.Arrival.insert(goods_type=self.goods_type,
                                                location=self.incoming_loc,
                                                state='planned',
                                                quantity=3)

        self.goods = Wms.Goods.insert(quantity=3,
                                      type=self.goods_type,
                                      location=self.incoming_loc,
                                      state='future',
                                      reason=self.arrival)
        self.Departure = Operation.Departure
        self.Goods = Wms.Goods

    def assertQuantities(self, loc=None, **quantities):
        if loc is None:
            loc = self.incoming_loc
        for state, qty in quantities.items():
            self.assertEqual(loc.quantity(self.goods_type, goods_state=state),
                             qty)

    def test_whole_planned_execute(self):
        dep = self.Departure.create(quantity=3,
                                    state='planned',
                                    goods=self.goods)

        self.assertEqual(dep.follows, [self.arrival])
        self.assertEqual(dep.goods, self.goods)

        self.goods.state = 'present'
        self.assertQuantities(future=0, present=3, past=0)

        dep.execute()
        self.assertEqual(dep.state, 'done')

        sent = self.Goods.query().filter(self.Goods.reason == dep).all()
        self.assertEqual(len(sent), 1)
        sent = sent[0]
        self.assertEqual(sent.state, 'past')
        self.assertEqual(sent.reason, dep)

        self.assertQuantities(future=0, present=0, past=3)

    def test_whole_done(self):
        self.goods.update(state='present')
        dep = self.Departure.create(quantity=3,
                                    state='done',
                                    goods=self.goods)

        self.assertEqual(dep.follows, [self.arrival])
        self.assertEqual(dep.goods, self.goods)
        self.assertQuantities(future=0, present=0, past=3)
        self.assertEqual(self.goods.reason, dep)

    def test_partial_done(self):
        self.goods.state = 'present'
        dep = self.Departure.create(quantity=1,
                                    state='done',
                                    goods=self.goods)

        self.assertEqual(dep.follows.type, ['wms_split'])
        self.assertEqual(dep.follows[0].follows, [self.arrival])

        sent = self.Goods.query().filter(self.Goods.reason == dep).all()
        self.assertEqual(len(sent), 1)
        sent = sent[0]
        self.assertEqual(sent.state, 'past')
        self.assertEqual(sent.quantity, 1)
        self.assertQuantities(future=2, present=2, past=1)

    def test_partial_planned_execute(self):
        dep = self.Departure.create(quantity=1,
                                    state='planned',
                                    goods=self.goods)

        self.assertEqual(dep.follows.type, ['wms_split'])
        self.assertEqual(dep.follows[0].follows, [self.arrival])

        self.goods.state = 'present'
        self.assertQuantities(future=2, present=3, past=0)
        dep.execute()

        sent = self.Goods.query().filter(self.Goods.reason == dep).all()
        self.assertEqual(len(sent), 1)
        sent = sent[0]
        self.assertEqual(sent.state, 'past')
        self.assertEqual(sent.quantity, 1)
        self.assertQuantities(future=2, present=2, past=1)
