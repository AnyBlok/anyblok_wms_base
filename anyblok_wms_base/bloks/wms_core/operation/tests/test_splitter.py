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
    OperationQuantityError,
    OperationMissingQuantityError,
)


class TestSplitterOperation(WmsTestCase):
    """Test the WmsSingleGoodOperation mixin

    In these test cases, Operation.Move is considered the canonical example of
    the mixin.
    """
    def setUp(self):
        super(TestSplitterOperation, self).setUp()
        Wms = self.registry.Wms
        Operation = Wms.Operation
        self.goods_type = Wms.Goods.Type.insert(label="My good type")
        self.incoming_loc = Wms.Location.insert(label="Incoming location")
        self.stock = Wms.Location.insert(label="Stock")

        self.arrival = Operation.Arrival.insert(goods_type=self.goods_type,
                                                location=self.incoming_loc,
                                                state='planned',
                                                dt_execution=self.dt_test1,
                                                quantity=3)

        self.goods = Wms.Goods.insert(quantity=3,
                                      type=self.goods_type,
                                      location=self.incoming_loc,
                                      state='future',
                                      dt_from=self.dt_test1,
                                      reason=self.arrival)
        self.Move = Operation.Move
        self.Goods = Wms.Goods
        self.op_model_name = 'Model.Wms.Operation.Move'

    def test_missing_quantity(self):
        # TODO should go to test_splitter
        self.goods.state = 'present'
        with self.assertRaises(OperationMissingQuantityError) as arc:
            self.Move.create(destination=self.stock,
                             dt_execution=self.dt_test2,
                             state='done',
                             input=self.goods)
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)

    def test_too_much(self):
        # TODO should go to test_splitter
        self.goods.state = 'present'
        with self.assertRaises(OperationQuantityError) as arc:
            self.Move.create(destination=self.stock,
                             dt_execution=self.dt_test2,
                             quantity=7,
                             state='done',
                             input=self.goods)
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)
        self.assertEqual(exc.kwargs.get('op_quantity'), 7)
        self.assertEqual(exc.kwargs.get('input'), self.goods)

    def test_quantity_changed_no_split(self):
        """SingleGoodsSplitters demand exact quantity (no split)"""
        # TODO splitter concrete classes now shouldn't care about quantity
        # the implementation should be in the SingleInput mixin
        move = self.Move.create(destination=self.stock,
                                quantity=3,
                                dt_execution=self.dt_test2,
                                state='planned',
                                input=self.goods)
        self.assertEqual(move.follows, [self.arrival])
        self.assertEqual(move.input, self.goods)
        self.goods.state = 'present'
        self.goods.quantity = 2
        self.registry.flush()
        with self.assertRaises(OperationQuantityError) as arc:
            move.execute()
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)
        self.assertEqual(exc.kwargs.get('inputs'), [self.goods])

    def test_quantity_changed_split(self):
        """SingleGoodsSplitters demand exact quantity (after split)

        We have to alter the split outcome somewhat artificially,
        to simulate a bug or some external alteration.
        """
        move = self.Move.create(destination=self.stock,
                                quantity=2,
                                dt_execution=self.dt_test2,
                                state='planned',
                                input=self.goods)
        self.assertNotEqual(move.input, self.goods)
        move.input.quantity = 3

        self.goods.state = 'present'
        self.registry.flush()
        with self.assertRaises(OperationQuantityError) as arc:
            move.execute()
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)
        self.assertEqual(exc.kwargs.get('inputs'), move.inputs)

    def test_quantity_too_big_split(self):
        # TODO should go to test_splitter
        move = self.Move.create(destination=self.stock,
                                quantity=2,
                                dt_execution=self.dt_test2,
                                state='planned',
                                input=self.goods)
        self.assertEqual(len(move.follows), 1)
        split = move.follows[0]
        self.assertEqual(split.input, self.goods)
        self.goods.update(quantity=1, state='present')

        with self.assertRaises(OperationQuantityError) as arc:
            split.execute()
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.model_name, 'Model.Wms.Operation.Split')
        self.assertEqual(exc.kwargs.get('inputs'), [self.goods])

    def test_repr(self):
        """For splitter operations, quantity is displayed in repr() and str()

        The Splitter mixin is actually the one introducing the quantity field.
        """
        move = self.Move.create(destination=self.stock,
                                quantity=3,
                                state='planned',
                                dt_execution=self.dt_test1,
                                input=self.goods)
        repr(move)
        str(move)
