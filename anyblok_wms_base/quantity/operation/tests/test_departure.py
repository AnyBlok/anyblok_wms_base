# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCaseWithPhysObj


class TestDeparture(WmsTestCaseWithPhysObj):

    arrival_kwargs = dict(quantity=3)

    def setUp(self):
        super(TestDeparture, self).setUp()
        self.Departure = self.Operation.Departure

    def assert_quantities(self, loc=None, **quantities):
        if loc is None:
            loc = self.incoming_loc
        for state, info in quantities.items():
            if state == 'present':
                qty, at_datetime, add_state = info, None, None
            else:
                qty, at_datetime = info
                add_state = [state]
            self.assert_quantity(qty,
                                 location=loc,
                                 additional_states=add_state,
                                 at_datetime=at_datetime)

    def test_partial_done(self):
        self.avatar.state = 'present'
        dep = self.Departure.create(quantity=1,
                                    state='done',
                                    dt_execution=self.dt_test2,
                                    input=self.avatar)

        self.assertEqual(dep.follows[0].type, 'wms_split')
        self.assertEqual(dep.follows[0].follows, [self.arrival])

        sent = dep.input
        self.assertEqual(sent.state, 'past')
        self.assertEqual(sent.dt_until, self.dt_test2)
        self.assertEqual(sent.obj.quantity, 1)
        # dt_until being exclusive, at self.dt_test2 the
        # physical objects were already sent.
        self.assert_quantities(future=(2, self.dt_test2),
                               present=2,
                               past=(2, self.dt_test2))
        # ... and at self.dt_test1, we still had the original ones
        self.assert_quantities(future=(2, self.dt_test2),
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
        self.assert_quantities(future=(2, self.dt_test2),
                               present=3,
                               past=(3, self.dt_test1))
        self.assert_quantities(past=(3, self.dt_test1))
        dep.execute(dt_execution=self.dt_test3)

        sent = dep.input
        self.assertEqual(sent.state, 'past')
        self.assertEqual(sent.dt_until, self.dt_test3)
        self.assertEqual(sent.obj.quantity, 1)
        # dt_until being exclusive,
        # at self.dt_test3 the physical objects were already sent,
        # at self.dt_test2, they aren't yet
        self.assert_quantities(future=(2, self.dt_test3),
                               present=2,
                               past=(2, self.dt_test3))
        self.assert_quantities(past=(3, self.dt_test2))

    def test_repr(self):
        dep = self.Departure.create(quantity=3,
                                    state='planned',
                                    dt_execution=self.dt_test2,
                                    input=self.avatar)
        repr(dep)
        str(dep)


del WmsTestCaseWithPhysObj
