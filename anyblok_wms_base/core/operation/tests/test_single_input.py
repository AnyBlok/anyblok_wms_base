# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCaseWithPhysObj
from anyblok_wms_base.exceptions import (
    OperationError,
    OperationInputsError,
    OperationMissingInputsError,
)


class TestSingleInputOperation(WmsTestCaseWithPhysObj):
    """Test the WmsSingleInputOperation mixin

    In these test cases, Operation.Move is considered the canonical example of
    the mixin. TODO should be Split actually, because that's the unique
    non splitter example we have.
    """
    def setUp(self):
        super(TestSingleInputOperation, self).setUp()
        self.op_model_name = 'Model.Wms.Operation.Move'
        self.Move = self.registry.Wms.Operation.Move

    def create(self, state='done', **kwargs):
        self.avatar.state = 'present'
        return self.Move.create(destination=self.stock,
                                state='done', **kwargs)

    def test_create_input(self):
        """Test that in create(), the input kwarg works."""
        avatar = self.avatar
        move = self.create(input=avatar)
        self.assertEqual(move.inputs, [avatar])

    def test_create_inputs(self):
        """Test that in create(), the inputs kwarg works."""
        avatar = self.avatar
        move = self.create(inputs=[avatar])
        self.assertEqual(move.inputs, [avatar])

    def test_create_both_input_args(self):
        """Test that in create(), using both input and inputs kwars is an error.
        """
        avatar = self.avatar
        with self.assertRaises(OperationError) as arc:
            self.create(inputs=[avatar], input=avatar)
        self.assertEqual(arc.exception.kwargs,
                         dict(input=avatar, inputs=[avatar]))

    def test_input_attr(self):
        move = self.Move.create(destination=self.stock,
                                inputs=[self.avatar],
                                state='planned', dt_execution=self.dt_test2)
        self.assertEqual(move.input, self.avatar)

    def test_whole_done_but_not_ready(self):
        # TODO should go to test_operation
        self.assertEqual(self.avatar.state, 'future')
        with self.assertRaises(OperationInputsError) as arc:
            self.Move.create(destination=self.stock,
                             dt_execution=self.dt_test2,
                             state='done',
                             input=self.avatar)
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)
        self.assertEqual(exc.kwargs.get('record'), self.avatar)
        self.assertEqual(list(exc.kwargs.get('inputs')), [self.avatar])

    def test_missing_goods(self):
        # TODO should go to test_operation
        self.avatar.state = 'present'
        with self.assertRaises(OperationMissingInputsError) as arc:
            self.Move.create(destination=self.stock,
                             dt_execution=self.dt_test2,
                             state='done')
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)

    def test_planned_execute_but_not_ready(self):
        # TODO should go to test_operation
        move = self.Move.create(destination=self.stock,
                                dt_execution=self.dt_test2,
                                state='planned',
                                input=self.avatar)
        self.assert_singleton(move.follows, value=self.arrival)
        self.assertEqual(move.input, self.avatar)
        with self.assertRaises(OperationInputsError) as arc:
            move.execute()
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)
        self.assertEqual(list(exc.kwargs.get('inputs')), [self.avatar])
        self.assertEqual(exc.kwargs.get('record'), self.avatar)


del WmsTestCaseWithPhysObj
