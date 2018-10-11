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
    OperationQuantityError,
    OperationMissingQuantityError,
)


class TestSplitterOperation(WmsTestCaseWithPhysObj):
    """Test the WmsSingleGoodOperation mixin

    In these test cases, Operation.Move is considered the canonical example of
    the mixin.
    """
    arrival_kwargs = dict(quantity=3)
    """Used in setUpSharedData()."""

    def setUp(self):
        super(TestSplitterOperation, self).setUp()
        self.Move = self.Operation.Move
        self.op_model_name = 'Model.Wms.Operation.Move'

    def test_missing_quantity(self):
        self.avatar.state = 'present'
        with self.assertRaises(OperationMissingQuantityError) as arc:
            self.Move.create(destination=self.stock,
                             dt_execution=self.dt_test2,
                             state='done',
                             input=self.avatar)
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)

    def test_too_much(self):
        self.avatar.state = 'present'
        with self.assertRaises(OperationQuantityError) as arc:
            self.Move.create(destination=self.stock,
                             dt_execution=self.dt_test2,
                             quantity=7,
                             state='done',
                             input=self.avatar)
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)
        self.assertEqual(exc.kwargs.get('op_quantity'), 7)
        self.assertEqual(exc.kwargs.get('input'), self.avatar)

    def test_quantity_changed_no_split(self):
        """Splitters demand exact quantity (no split)"""
        # TODO splitter concrete classes now shouldn't care about quantity
        # the implementation should be in the SingleInput mixin
        move = self.Move.create(destination=self.stock,
                                quantity=3,
                                dt_execution=self.dt_test2,
                                state='planned',
                                input=self.avatar)
        self.assertEqual(move.follows, [self.arrival])
        self.assertEqual(move.input, self.avatar)
        self.avatar.state = 'present'
        self.physobj.quantity = 2
        self.registry.flush()
        with self.assertRaises(OperationQuantityError) as arc:
            move.execute()
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)
        self.assertEqual(exc.kwargs.get('inputs'), [self.avatar])

    def test_quantity_changed_split(self):
        """Splitters demand exact quantity (after split)

        We have to alter the split outcome somewhat artificially,
        to simulate a bug or some external alteration.
        """
        move = self.Move.create(destination=self.stock,
                                quantity=2,
                                dt_execution=self.dt_test2,
                                state='planned',
                                input=self.avatar)
        self.assertNotEqual(move.input, self.avatar)
        move.input.obj.quantity = 3

        self.avatar.state = 'present'
        self.registry.flush()
        with self.assertRaises(OperationQuantityError) as arc:
            move.execute()
        exc = arc.exception
        self.assertEqual(exc.model_name, self.op_model_name)
        self.assertEqual(exc.kwargs.get('inputs'), move.inputs)

    def test_quantity_too_big_split(self):
        move = self.Move.create(destination=self.stock,
                                quantity=2,
                                dt_execution=self.dt_test2,
                                state='planned',
                                input=self.avatar)
        split = self.assert_singleton(move.follows)
        self.assertEqual(split.input, self.avatar)
        self.physobj.quantity = 1
        self.avatar.state = 'present'

        with self.assertRaises(OperationQuantityError) as arc:
            split.execute()
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.model_name, 'Model.Wms.Operation.Split')
        self.assertEqual(exc.kwargs.get('inputs'), [self.avatar])

    def test_repr(self):
        """For splitter operations, quantity is displayed in repr() and str()

        The Splitter mixin is actually the one introducing the quantity field.
        """
        move = self.Move.create(destination=self.stock,
                                quantity=3,
                                state='planned',
                                dt_execution=self.dt_test1,
                                input=self.avatar)
        repr(move)
        str(move)


del WmsTestCaseWithPhysObj
