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

    arrival_kwargs = dict(quantity=3)

    def setUp(self):
        super(TestDeparture, self).setUp()
        self.Departure = self.Operation.Departure

    def assertQuantities(self, loc=None, **quantities):
        if loc is None:
            loc = self.incoming_loc
        for state, info in quantities.items():
            if state == 'present':
                qty, at_datetime, add_state = info, None, None
            else:
                qty, at_datetime = info
                add_state = [state]
            self.assertEqual(self.Wms.quantity(location=loc,
                                               goods_type=self.goods_type,
                                               additional_states=add_state,
                                               at_datetime=at_datetime),
                             qty)

    def test_partial_done(self):
        self.avatar.state = 'present'
        dep = self.Departure.create(quantity=1,
                                    state='done',
                                    dt_execution=self.dt_test2,
                                    input=self.avatar)

        self.assertEqual(dep.follows[0].type, 'wms_split')
        self.assertEqual(dep.follows[0].follows, [self.arrival])

        sent = self.single_result(
            self.Avatar.query().filter(self.Avatar.reason == dep))
        self.assertEqual(sent.state, 'past')
        self.assertEqual(sent.dt_until, self.dt_test2)
        self.assertEqual(sent.goods.quantity, 1)
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
                                    input=self.avatar)

        self.assertEqual(dep.follows[0].type, 'wms_split')
        self.assertEqual(dep.follows[0].follows, [self.arrival])

        self.avatar.state = 'present'
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
        self.assertEqual(sent.goods.quantity, 1)
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
                                    input=self.avatar)
        repr(dep)
        str(dep)


del WmsTestCaseWithGoods
