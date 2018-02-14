# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok.tests.testcase import BlokTestCase
from anyblok_wms_base.exceptions import (
    OperationGoodsError,
    OperationMissingGoodsError,
    OperationQuantityError,
    OperationMissingQuantityError,
)


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

    def test_whole_done(self):
        self.goods.update(state='present')
        move = self.Move.create(destination=self.stock,
                                quantity=3,
                                state='done',
                                goods=self.goods)
        self.assertEqual(move.follows, [self.arrival])

    def test_partial_done(self):
        self.goods.update(state='present')
        move = self.Move.create(destination=self.stock,
                                quantity=1,
                                state='done',
                                goods=self.goods)
        self.assertEqual(len(move.follows), 1)
        split = move.follows[0]
        self.assertEqual(split.type, 'wms_split')

        self.assertEqual(self.goods.quantity, 2)

        after_move = self.Goods.query().filter(self.Goods.reason == move).all()
        self.assertEqual(len(after_move), 1)

        after_move = after_move[0]
        self.assertEqual(after_move.quantity, 1)
        self.assertEqual(after_move.location, self.stock)
        self.assertEqual(after_move.reason, move)

    def test_partial_planned_execute(self):
        move = self.Move.create(destination=self.stock,
                                quantity=1,
                                state='planned',
                                goods=self.goods)
        self.assertEqual(len(move.follows), 1)
        split = move.follows[0]
        self.assertEqual(split.type, 'wms_split')

        self.goods.state = 'present'
        self.registry.flush()
        move.execute()

        self.assertEqual(self.goods.quantity, 2)

        after_move = self.Goods.query().filter(self.Goods.reason == move).all()
        self.assertEqual(len(after_move), 1)

        after_move = after_move[0]
        self.assertEqual(after_move.quantity, 1)
        self.assertEqual(after_move.location, self.stock)
        self.assertEqual(after_move.reason, move)
        self.assertEqual(after_move.state, 'present')


class TestSingleGoodsOperation(BlokTestCase):
    """Test the WmsSingleGoodOperation mixin

    In these test cases, Operation.Move is considered the canonical example of
    the mixin.
    """
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
        self.op_model_name = 'Model.Wms.Operation.Move'

    def test_whole_done_but_not_ready(self):
        self.assertEqual(self.goods.state, 'future')
        with self.assertRaises(OperationGoodsError) as arc:
            self.Move.create(destination=self.stock,
                             quantity=3,
                             state='done',
                             goods=self.goods)
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)
        self.assertEqual(exc.kwargs.get('goods'), self.goods)

    def test_missing_quantity(self):
        self.goods.state = 'present'
        with self.assertRaises(OperationMissingQuantityError) as arc:
            self.Move.create(destination=self.stock,
                             state='done',
                             goods=self.goods)
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)

    def test_missing_goods(self):
        self.goods.state = 'present'
        with self.assertRaises(OperationMissingGoodsError) as arc:
            self.Move.create(destination=self.stock,
                             state='done',
                             quantity=3)
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)

    def test_too_much(self):
        self.goods.state = 'present'
        with self.assertRaises(OperationQuantityError) as arc:
            self.Move.create(destination=self.stock,
                             quantity=7,
                             state='done',
                             goods=self.goods)
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)
        self.assertEqual(exc.kwargs.get('quantity'), 7)
        self.assertEqual(exc.kwargs.get('goods'), self.goods)

    def test_whole_planned_execute_but_not_ready(self):
        move = self.Move.create(destination=self.stock,
                                quantity=3,
                                state='planned',
                                goods=self.goods)
        self.assertEqual(move.follows, [self.arrival])
        self.assertEqual(move.goods, self.goods)
        with self.assertRaises(OperationGoodsError) as arc:
            move.execute()
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)
        self.assertEqual(exc.kwargs.get('goods'), self.goods)

    def test_quantity_changed_no_split(self):
        """SingleGoodsSplitters raise if quantity of the final op isn't exact.

        This test is for the case without split
        """
        move = self.Move.create(destination=self.stock,
                                quantity=3,
                                state='planned',
                                goods=self.goods)
        self.assertEqual(move.follows, [self.arrival])
        self.assertEqual(move.goods, self.goods)
        self.goods.state = 'present'
        self.goods.quantity = 2
        with self.assertRaises(OperationQuantityError) as arc:
            move.execute()
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)
        self.assertEqual(exc.kwargs.get('goods'), self.goods)

    def test_quantity_changed_split(self):
        """SingleGoodsSplitters raise if quantity of the final op isn't exact.

        This test is for the case with split. We have to alter the split
        outcome somewhat artificially, to simulate a bug or some external
        alteration.
        """
        move = self.Move.create(destination=self.stock,
                                quantity=2,
                                state='planned',
                                goods=self.goods)
        self.assertNotEqual(move.goods, self.goods)
        move.goods.quantity = 3

        self.goods.state = 'present'
        with self.assertRaises(OperationQuantityError) as arc:
            move.execute()
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)
        self.assertEqual(exc.kwargs.get('goods'), move.goods)

    def test_quantity_too_big_split(self):
        move = self.Move.create(destination=self.stock,
                                quantity=2,
                                state='planned',
                                goods=self.goods)
        self.assertEqual(len(move.follows), 1)
        split = move.follows[0]
        self.assertEqual(split.goods, self.goods)
        self.goods.quantity = 1

        with self.assertRaises(OperationQuantityError) as arc:
            split.execute()
        exc = arc.exception
        self.assertEqual(exc.model_name, 'Model.Wms.Operation.Split')
        self.assertEqual(exc.kwargs.get('goods'), self.goods)

    def test_repr(self):
        move = self.Move(destination=self.stock,
                         quantity=3,
                         state='planned',
                         goods=self.goods)
        repr(move)
        str(move)
