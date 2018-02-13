# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok.tests.testcase import BlokTestCase
from anyblok_wms_base.exceptions import OperationCreateArgFollows


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
                                      goods_code='765',
                                      goods_properties=dict(foo=5,
                                                            bar='monty'),
                                      goods_type=self.goods_type)
        self.assertEqual(arrival.follows, [])
        arrived = self.Goods.query().filter(self.Goods.reason == arrival).all()
        self.assertEqual(len(arrived), 1)
        goods = arrived[0]
        self.assertEqual(goods.state, 'future')
        self.assertEqual(goods.location, self.incoming_loc)
        self.assertEqual(goods.quantity, 3)
        self.assertEqual(goods.type, self.goods_type)
        self.assertEqual(goods.code, '765')
        self.assertEqual(goods.get_property('foo'), 5)
        self.assertEqual(goods.get_property('bar'), 'monty')

        arrival.execute()
        self.assertEqual(goods.state, 'present')
        self.assertEqual(arrival.state, 'done')
        self.assertEqual(goods.get_property('foo'), 5)
        self.assertEqual(goods.get_property('bar'), 'monty')
        self.assertEqual(goods.code, '765')

    def test_create_done(self):
        arrival = self.Arrival.create(location=self.incoming_loc,
                                      quantity=3,
                                      state='done',
                                      goods_code='x34/7',
                                      goods_properties=dict(foo=2,
                                                            monty='python'),
                                      goods_type=self.goods_type)
        self.assertEqual(arrival.follows, [])
        arrived = self.Goods.query().filter(self.Goods.reason == arrival).all()
        self.assertEqual(len(arrived), 1)
        goods = arrived[0]
        self.assertEqual(goods.state, 'present')
        self.assertEqual(goods.location, self.incoming_loc)
        self.assertEqual(goods.quantity, 3)
        self.assertEqual(goods.type, self.goods_type)
        self.assertEqual(goods.code, 'x34/7')
        self.assertEqual(goods.get_property('foo'), 2)
        self.assertEqual(goods.get_property('monty'), 'python')


class TestOperationBase(BlokTestCase):
    """Test the Operation base class

    In these test cases, Operation.Move is considered the canonical example
    to test some corner cases in the base Operation model.
    """

    def setUp(self):
        Wms = self.registry.Wms
        self.goods_type = Wms.Goods.Type.insert(label="My good type")
        self.incoming_loc = Wms.Location.insert(label="Incoming location")
        self.stock = Wms.Location.insert(label="Stock")
        self.Arrival = Wms.Operation.Arrival
        self.Goods = Wms.Goods

    def test_execute_idempotency(self):
        op = self.Arrival.create(location=self.incoming_loc,
                                 quantity=3,
                                 state='planned',
                                 goods_type=self.goods_type)
        op.state = 'done'
        op.execute_planned = lambda: self.fail("Should not be called")
        op.execute()

    def test_forbidfollows(self):
        with self.assertRaises(OperationCreateArgFollows) as arc:
            self.Arrival.create(follows='anything triggers', state='whatever')
        str(arc.exception)
        repr(arc.exception)
