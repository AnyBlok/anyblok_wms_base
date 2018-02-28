# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from .testcase import WmsTestCase


class TestDeparture(WmsTestCase):

    def setUp(self):
        super(TestDeparture, self).setUp()
        Wms = self.registry.Wms
        Operation = Wms.Operation
        self.goods_type = Wms.Goods.Type.insert(label="My good type")
        self.incoming_loc = Wms.Location.insert(label="Incoming location")
        self.stock = Wms.Location.insert(label="Stock")

        self.arrival = Operation.Arrival.insert(goods_type=self.goods_type,
                                                location=self.incoming_loc,
                                                dt_execution=self.dt_test1,
                                                state='planned',
                                                quantity=3)
        self.Goods = Wms.Goods
        self.Avatar = Avatar = Wms.Goods.Avatar
        self.goods = Avatar.insert(
            goods=Wms.Goods.insert(quantity=3, type=self.goods_type),
            location=self.incoming_loc,
            state='future',
            dt_from=self.dt_test1,
            reason=self.arrival)
        self.Departure = Operation.Departure

    def assertQuantities(self, loc=None, **quantities):
        if loc is None:
            loc = self.incoming_loc
        for state, info in quantities.items():
            if state == 'present':
                qty, at_datetime = info, None
            else:
                qty, at_datetime = info
            self.assertEqual(loc.quantity(self.goods_type,
                                          goods_state=state,
                                          at_datetime=at_datetime),
                             qty)

    def test_whole_planned_execute(self):
        dep = self.Departure.create(quantity=3,
                                    state='planned',
                                    dt_execution=self.dt_test2,
                                    input=self.goods)

        self.assertEqual(dep.follows, [self.arrival])
        self.assertEqual(dep.input, self.goods)
        self.assertEqual(self.goods.dt_until, self.dt_test2)

        self.goods.state = 'present'
        self.assertQuantities(future=(0, self.dt_test2),
                              present=3,
                              past=(3, self.dt_test1))

        dep.execute(self.dt_test3)
        self.assertEqual(dep.state, 'done')

        sent = self.Avatar.query().filter(self.Avatar.reason == dep).all()
        self.assertEqual(len(sent), 1)
        sent = sent[0]
        self.assertEqual(sent.state, 'past')
        self.assertEqual(self.goods.dt_until, self.dt_test3)
        self.assertEqual(sent.reason, dep)

        self.assertQuantities(future=(0, self.dt_test2),
                              present=0,
                              past=(3, self.dt_test1))

    def test_whole_planned_execute_obliviate(self):
        self.goods.state = 'present'
        dep = self.Departure.create(quantity=3,
                                    state='planned',
                                    dt_execution=self.dt_test2,
                                    input=self.goods)
        dep.execute()
        dep.obliviate()

        new_goods = self.single_result(self.Avatar.query())
        self.assertEqual(new_goods.state, 'present')
        self.assertEqual(new_goods.quantity, 3)
        self.assertEqual(new_goods.dt_from, self.dt_test1)
        self.assertEqual(new_goods.location, self.incoming_loc)

    def test_whole_planned_cancel(self):
        self.goods.state = 'present'
        self.goods.dt_until = self.dt_test3
        dep = self.Departure.create(quantity=3,
                                    state='planned',
                                    dt_execution=self.dt_test2,
                                    input=self.goods)
        dep.cancel()

        new_goods = self.single_result(self.Avatar.query())
        self.assertEqual(new_goods.state, 'present')
        self.assertEqual(new_goods.dt_from, self.dt_test1)
        self.assertEqual(new_goods.dt_until, self.dt_test3)
        self.assertEqual(new_goods.quantity, 3)
        self.assertEqual(new_goods.location, self.incoming_loc)

    def test_whole_done(self):
        self.goods.update(state='present')
        dep = self.Departure.create(quantity=3,
                                    state='done',
                                    dt_execution=self.dt_test2,
                                    input=self.goods)

        self.assertEqual(dep.follows, [self.arrival])
        self.assertEqual(dep.input, self.goods)
        self.assertQuantities(future=(0, self.dt_test2),
                              present=0,
                              past=(3, self.dt_test1))
        self.assertEqual(self.goods.reason, dep)
        self.assertEqual(self.goods.state, 'past')
        self.assertEqual(self.goods.dt_until, self.dt_test2)

    def test_done_obliviate(self):
        self.goods.update(state='present')
        dep = self.Departure.create(quantity=3,
                                    state='done',
                                    dt_execution=self.dt_test2,
                                    input=self.goods)
        dep.obliviate()
        new_goods = self.single_result(self.Avatar.query())
        self.assertEqual(new_goods.state, 'present')
        self.assertEqual(new_goods.quantity, 3)
        self.assertEqual(new_goods.dt_from, self.dt_test1)
        self.assertEqual(new_goods.location, self.incoming_loc)

    def test_partial_done(self):
        self.goods.state = 'present'
        dep = self.Departure.create(quantity=1,
                                    state='done',
                                    dt_execution=self.dt_test2,
                                    input=self.goods)

        self.assertEqual(dep.follows[0].type, 'wms_split')
        self.assertEqual(dep.follows[0].follows, [self.arrival])

        sent = self.single_result(
            self.Avatar.query().filter(self.Avatar.reason == dep))
        self.assertEqual(sent.state, 'past')
        self.assertEqual(sent.dt_until, self.dt_test2)
        self.assertEqual(sent.quantity, 1)
        # dt_until being exclusive, at self.dt_test2 the
        # goods were already sent.
        self.assertQuantities(future=(2, self.dt_test2),
                              present=2,
                              past=(2, self.dt_test2))
        # ... and at self.dt_test1, we still had the original ones
        self.assertQuantities(future=(2, self.dt_test2),
                              present=2,
                              past=(3, self.dt_test1))

    def test_partial_planned_execute(self):
        dep = self.Departure.create(quantity=1,
                                    state='planned',
                                    dt_execution=self.dt_test2,
                                    input=self.goods)

        self.assertEqual(dep.follows[0].type, 'wms_split')
        self.assertEqual(dep.follows[0].follows, [self.arrival])

        self.goods.state = 'present'
        self.assertQuantities(future=(2, self.dt_test2),
                              present=3,
                              past=(3, self.dt_test1))
        self.assertQuantities(past=(3, self.dt_test1))
        dep.execute(dt_execution=self.dt_test3)

        sent = self.Avatar.query().filter(self.Avatar.reason == dep).all()
        self.assertEqual(len(sent), 1)
        sent = sent[0]
        self.assertEqual(sent.state, 'past')
        self.assertEqual(sent.dt_until, self.dt_test3)
        self.assertEqual(sent.quantity, 1)
        # dt_until being exclusive, at self.dt_test3 the
        # goods were already sent, at self.dt_test2, they aren't yet
        self.assertQuantities(future=(2, self.dt_test3),
                              present=2,
                              past=(2, self.dt_test3))
        self.assertQuantities(past=(3, self.dt_test2))

    def test_repr(self):
        dep = self.Departure.create(quantity=3,
                                    state='planned',
                                    dt_execution=self.dt_test2,
                                    input=self.goods)
        repr(dep)
        str(dep)
