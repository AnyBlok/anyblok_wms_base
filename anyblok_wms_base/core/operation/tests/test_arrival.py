# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from .testcase import WmsTestCase

from anyblok_wms_base.exceptions import (
    OperationContainerExpected,
)


class TestArrival(WmsTestCase):

    def setUp(self):
        super(TestArrival, self).setUp()
        PhysObj = self.PhysObj
        self.goods_type = PhysObj.Type.insert(label="My good type",
                                              code='MGT')
        self.incoming_loc = self.insert_location('INCOMING')
        self.stock = self.insert_location('STOCK')

        self.Arrival = self.Operation.Arrival
        self.Avatar = self.PhysObj.Avatar

    def test_create_planned_execute(self):
        arrival = self.Arrival.create(location=self.incoming_loc,
                                      state='planned',
                                      dt_execution=self.dt_test1,
                                      goods_code='765',
                                      goods_properties=dict(foo=5,
                                                            bar='monty'),
                                      goods_type=self.goods_type)
        self.assertEqual(len(arrival.follows), 0)
        avatar = self.assert_singleton(arrival.outcomes)
        goods = avatar.obj
        self.assertEqual(avatar.state, 'future')
        self.assertEqual(avatar.location, self.incoming_loc)
        self.assertEqual(goods.type, self.goods_type)
        self.assertEqual(goods.code, '765')
        self.assertEqual(goods.get_property('foo'), 5)
        self.assertEqual(goods.get_property('bar'), 'monty')
        self.assertEqual(avatar.dt_from, self.dt_test1)

        arrival.execute(self.dt_test2)
        self.assertEqual(arrival.state, 'done')
        self.assertEqual(arrival.dt_execution, self.dt_test2)
        self.assertEqual(arrival.dt_start, self.dt_test2)
        self.assertEqual(avatar.state, 'present')
        self.assertEqual(goods.get_property('foo'), 5)
        self.assertEqual(goods.get_property('bar'), 'monty')
        self.assertEqual(goods.code, '765')
        self.assertEqual(avatar.dt_from, self.dt_test2)

    def test_create_done(self):
        arrival = self.Arrival.create(location=self.incoming_loc,
                                      state='done',
                                      goods_code='x34/7',
                                      goods_properties=dict(foo=2,
                                                            monty='python'),
                                      goods_type=self.goods_type)
        self.assertEqual(len(arrival.follows), 0)
        avatar = self.assert_singleton(arrival.outcomes)
        goods = avatar.obj
        self.assertEqual(avatar.state, 'present')
        self.assertEqual(avatar.location, self.incoming_loc)
        self.assertEqual(goods.type, self.goods_type)
        self.assertEqual(goods.code, 'x34/7')
        self.assertEqual(goods.get_property('foo'), 2)
        self.assertEqual(goods.get_property('monty'), 'python')

    def test_arrival_done_obliviate(self):
        arrival = self.Arrival.create(location=self.incoming_loc,
                                      state='done',
                                      goods_code='x34/7',
                                      goods_properties=dict(foo=2,
                                                            monty='python'),
                                      goods_type=self.goods_type)
        arrival.obliviate()
        self.assertEqual(self.Avatar.query().count(), 0)
        self.assertEqual(
            self.PhysObj.query().filter_by(type=self.goods_type).count(), 0)

    def test_arrival_planned_execute_obliviate(self):
        arrival = self.Arrival.create(location=self.incoming_loc,
                                      state='planned',
                                      dt_execution=self.dt_test1,
                                      goods_code='x34/7',
                                      goods_properties=dict(foo=2,
                                                            monty='python'),
                                      goods_type=self.goods_type)
        arrival.execute()
        arrival.obliviate()
        self.assertEqual(self.Avatar.query().count(), 0)
        self.assertEqual(
            self.PhysObj.query().filter_by(type=self.goods_type).count(), 0)

    def test_repr(self):
        arrival = self.Arrival(location=self.incoming_loc,
                               state='done',
                               goods_code='x34/7',
                               goods_properties=dict(foo=2,
                                                     monty='python'),
                               goods_type=self.goods_type)
        repr(arrival)
        str(arrival)

    def test_not_a_container(self):
        wrong_loc = self.PhysObj.insert(type=self.goods_type)
        with self.assertRaises(OperationContainerExpected) as arc:
            self.Arrival.create(
                location=wrong_loc,
                state='done',
                goods_type=self.goods_type)
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['offender'], wrong_loc)
