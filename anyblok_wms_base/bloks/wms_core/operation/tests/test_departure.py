# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCaseWithGoods


class TestDeparture(WmsTestCaseWithGoods):

    def setUp(self):
        super(TestDeparture, self).setUp()
        Wms = self.registry.Wms
        Operation = Wms.Operation
        self.stock = Wms.Location.insert(label="Stock")
        self.Departure = Operation.Departure

    def assertQuantities(self, loc=None, **quantities):
        if loc is None:
            loc = self.incoming_loc
        for state, info in quantities.items():
            if state == 'present':
                qty, at_datetime, add_state = info, None, None
            else:
                qty, at_datetime = info
                add_state = [state]
            self.assertEqual(loc.quantity(self.goods_type,
                                          additional_states=add_state,
                                          at_datetime=at_datetime),
                             qty)

    def test_whole_planned_execute(self):
        dep = self.Departure.create(state='planned',
                                    dt_execution=self.dt_test2,
                                    input=self.goods)

        self.assertEqual(dep.follows, [self.arrival])
        self.assertEqual(dep.input, self.goods)
        self.assertEqual(self.goods.dt_until, self.dt_test2)

        self.goods.state = 'present'
        self.assertQuantities(future=(0, self.dt_test2),
                              present=1,
                              past=(1, self.dt_test1))

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
                              past=(1, self.dt_test1))

    def test_whole_planned_execute_obliviate(self):
        self.goods.state = 'present'
        dep = self.Departure.create(state='planned',
                                    dt_execution=self.dt_test2,
                                    input=self.goods)
        dep.execute()
        dep.obliviate()

        new_goods = self.single_result(self.Avatar.query())
        self.assertEqual(new_goods.state, 'present')
        self.assertEqual(new_goods.dt_from, self.dt_test1)
        self.assertEqual(new_goods.location, self.incoming_loc)

    def test_whole_planned_cancel(self):
        self.goods.state = 'present'
        self.goods.dt_until = self.dt_test3
        dep = self.Departure.create(state='planned',
                                    dt_execution=self.dt_test2,
                                    input=self.goods)
        dep.cancel()

        new_goods = self.single_result(self.Avatar.query())
        self.assertEqual(new_goods.state, 'present')
        self.assertEqual(new_goods.dt_from, self.dt_test1)
        self.assertEqual(new_goods.dt_until, self.dt_test3)
        self.assertEqual(new_goods.location, self.incoming_loc)

    def test_whole_done(self):
        self.goods.update(state='present')
        dep = self.Departure.create(state='done',
                                    dt_execution=self.dt_test2,
                                    input=self.goods)

        self.assertEqual(dep.follows, [self.arrival])
        self.assertEqual(dep.input, self.goods)
        self.assertQuantities(future=(0, self.dt_test2),
                              present=0,
                              past=(1, self.dt_test1))
        self.assertEqual(self.goods.reason, dep)
        self.assertEqual(self.goods.state, 'past')
        self.assertEqual(self.goods.dt_until, self.dt_test2)

    def test_done_obliviate(self):
        self.goods.update(state='present')
        dep = self.Departure.create(state='done',
                                    dt_execution=self.dt_test2,
                                    input=self.goods)
        dep.obliviate()
        new_goods = self.single_result(self.Avatar.query())
        self.assertEqual(new_goods.state, 'present')
        self.assertEqual(new_goods.dt_from, self.dt_test1)
        self.assertEqual(new_goods.location, self.incoming_loc)

    def test_repr(self):
        dep = self.Departure.create(state='planned',
                                    dt_execution=self.dt_test2,
                                    input=self.goods)
        repr(dep)
        str(dep)
