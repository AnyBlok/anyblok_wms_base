# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from .testcase import WmsTestCase


class TestMove(WmsTestCase):

    def setUp(self):
        super(TestMove, self).setUp()
        Wms = self.registry.Wms
        Operation = Wms.Operation
        goods_type = Wms.Goods.Type.insert(label="My good type")
        self.incoming_loc = Wms.Location.insert(label="Incoming location")
        self.stock = Wms.Location.insert(label="Stock")

        self.arrival = Operation.Arrival.insert(goods_type=goods_type,
                                                location=self.incoming_loc,
                                                state='planned',
                                                dt_execution=self.dt_test1,
                                                quantity=3)

        self.goods = Wms.Goods.insert(quantity=3,
                                      type=goods_type,
                                      location=self.incoming_loc,
                                      dt_from=self.dt_test1,
                                      dt_until=self.dt_test3,
                                      state='future',
                                      reason=self.arrival)
        self.Move = Operation.Move
        self.Goods = Wms.Goods

    def assertBackToBeginning(self):
        new_goods = self.single_result(self.Goods.query())
        self.assertEqual(new_goods.quantity, 3)
        self.assertEqual(new_goods.location, self.incoming_loc)
        self.assertEqual(new_goods.state, 'present')
        self.assertEqual(new_goods.dt_from, self.dt_test1)
        self.assertEqual(new_goods.dt_until, self.dt_test3)
        self.assertEqual(new_goods.reason, self.arrival)
        # TODO also check that id did not change once we can make it True

    def test_whole_planned_execute(self):
        move = self.Move.create(destination=self.stock,
                                quantity=3,
                                state='planned',
                                dt_execution=self.dt_test2,
                                input=self.goods)
        self.assertEqual(move.follows, [self.arrival])
        self.assertEqual(move.input, self.goods)
        self.goods.update(state='present')

        move.execute()
        self.assertEqual(move.state, 'done')
        self.assertEqual(self.goods.reason, move)

        moved = self.single_result(
            self.Goods.query().filter(self.Goods.reason == move,
                                      self.Goods.state != 'past'))
        self.assertEqual(moved.state, 'present')
        self.assertEqual(moved.reason, move)
        self.assertEqual(moved.location, self.stock)
        self.assertEqual(self.Goods.query().filter(
            self.Goods.location == self.incoming_loc,
            self.Goods.state != 'past').count(), 0)

    def test_whole_done(self):
        self.goods.update(state='present')
        move = self.Move.create(destination=self.stock,
                                quantity=3,
                                state='done',
                                dt_execution=self.dt_test2,
                                input=self.goods)
        self.assertEqual(move.follows, [self.arrival])

        after_move = move.outcomes[0]
        self.assertEqual(after_move.quantity, 3)
        self.assertEqual(after_move.location, self.stock)
        self.assertEqual(after_move.state, 'present')
        self.assertEqual(after_move.reason, move)

        not_moved = move.input
        self.assertEqual(not_moved.state, 'past')

    def test_whole_done_obliviate(self):
        self.goods.state = 'present'
        move = self.Move.create(destination=self.stock,
                                quantity=3,
                                state='done',
                                input=self.goods)  # result already tested
        move.obliviate()
        self.assertBackToBeginning()

    def test_whole_planned_execute_obliviate(self):
        move = self.Move.create(destination=self.stock,
                                quantity=3,
                                dt_execution=self.dt_test2,
                                state='planned',
                                input=self.goods)
        self.goods.update(state='present')
        move.execute()  # result already tested
        move.obliviate()
        self.assertBackToBeginning()

    def test_partial_done(self):
        self.goods.update(state='present')
        move = self.Move.create(destination=self.stock,
                                quantity=1,
                                state='done',
                                dt_execution=self.dt_test2,
                                input=self.goods)
        split = self.assert_singleton(move.follows)
        self.assertEqual(split.type, 'wms_split')

        # the original has been thrown in the past by the split
        self.assertEqual(self.goods.quantity, 3)
        self.assertEqual(self.goods.state, 'past')
        self.assertEqual(self.goods.dt_from, self.dt_test1)
        self.assertEqual(self.goods.dt_until, self.dt_test2)

        not_moved = self.assert_singleton(split.outcomes)
        self.assertEqual(not_moved.quantity, 2)

        after_move = self.assert_singleton(move.outcomes)
        self.assertEqual(after_move.quantity, 1)
        self.assertEqual(after_move.dt_from, self.dt_test2)
        self.assertEqual(after_move.dt_until, self.dt_test3)
        self.assertEqual(after_move.location, self.stock)
        self.assertEqual(after_move.reason, move)

    def test_partial_planned_execute(self):
        move = self.Move.create(destination=self.stock,
                                quantity=1,
                                state='planned',
                                dt_execution=self.dt_test2,
                                input=self.goods)
        split = self.assert_singleton(move.follows)
        self.assertEqual(split.type, 'wms_split')

        self.goods.state = 'present'
        self.registry.flush()
        move.execute(dt_execution=self.dt_test2)

        # the original has been thrown in the past by the split
        self.assertEqual(self.goods.quantity, 3)
        self.assertEqual(self.goods.state, 'past')
        self.assertEqual(self.goods.dt_from, self.dt_test1)
        self.assertEqual(self.goods.dt_until, self.dt_test2)

        # the moved Goods are not considered an outcome of the Split,
        # because the Move is now its reason
        not_moved = self.assert_singleton(split.outcomes)
        self.assertEqual(not_moved.quantity, 2)

        after_move = self.assert_singleton(move.outcomes)
        self.assertEqual(after_move.quantity, 1)
        self.assertEqual(after_move.location, self.stock)
        self.assertEqual(after_move.dt_from, self.dt_test2)
        self.assertEqual(after_move.dt_until, self.dt_test3)
        self.assertEqual(after_move.reason, move)
        self.assertEqual(after_move.state, 'present')
