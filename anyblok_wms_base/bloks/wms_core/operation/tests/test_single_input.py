# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCaseWithGoods
from anyblok_wms_base.exceptions import (
    OperationError,
    OperationInputsError,
    OperationMissingInputsError,
)


class TestSingleInputOperation(WmsTestCaseWithGoods):
    """Test the WmsSingleInputOperation mixin

    In these test cases, Operation.Move is considered the canonical example of
    the mixin. TODO should be Split actually, because that's the unique
    non splitter example we have.
    """
    def setUp(self):
        super(TestSingleInputOperation, self).setUp()
        self.op_model_name = 'Model.Wms.Operation.Move'
        self.Move = self.registry.Wms.Operation.Move

    def test_create_input_inputs(self):
        """Test that in create(), the input and inputs kwargs work."""
        goods = self.goods

        def create(**kwargs):
            goods.state = 'present'
            return self.Move.create(destination=self.stock,
                                    state='done', **kwargs)

        move = create(input=goods)
        self.assertEqual(move.inputs, [goods])

        move = create(inputs=[goods])
        self.assertEqual(move.inputs, [goods])

        with self.assertRaises(OperationError) as arc:
            create(inputs=[goods], input=goods)
        self.assertEqual(arc.exception.kwargs,
                         dict(input=goods, inputs=[goods]))

    def test_input_attr(self):
        move = self.Move.create(destination=self.stock,
                                inputs=[self.goods],
                                state='planned', dt_execution=self.dt_test2)
        self.assertEqual(move.input, self.goods)

    def test_whole_done_but_not_ready(self):
        # TODO should go to test_operation
        self.assertEqual(self.goods.state, 'future')
        with self.assertRaises(OperationInputsError) as arc:
            self.Move.create(destination=self.stock,
                             dt_execution=self.dt_test2,
                             state='done',
                             input=self.goods)
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)
        self.assertEqual(exc.kwargs.get('record'), self.goods)
        self.assertEqual(list(exc.kwargs.get('inputs')), [self.goods])

    def test_missing_goods(self):
        # TODO should go to test_operation
        self.goods.state = 'present'
        with self.assertRaises(OperationMissingInputsError) as arc:
            self.Move.create(destination=self.stock,
                             dt_execution=self.dt_test2,
                             state='done')
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)

    def test_whole_planned_execute_but_not_ready(self):
        # TODO should go to test_operation
        move = self.Move.create(destination=self.stock,
                                dt_execution=self.dt_test2,
                                state='planned',
                                input=self.goods)
        self.assertEqual(move.follows, [self.arrival])
        self.assertEqual(move.input, self.goods)
        with self.assertRaises(OperationInputsError) as arc:
            move.execute()
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)
        self.assertEqual(list(exc.kwargs.get('inputs')), [self.goods])
        self.assertEqual(exc.kwargs.get('record'), self.goods)
