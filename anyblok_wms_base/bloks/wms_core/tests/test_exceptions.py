# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from datetime import datetime
from anyblok.tests.testcase import BlokTestCase
from anyblok_wms_base.exceptions import (
    OperationError,
    OperationInputsError,
    OperationInputWrongState,
    )


class TestOperationError(BlokTestCase):

    def setUp(self):
        self.dt_test1 = datetime.now()
        Wms = self.registry.Wms
        goods_type = Wms.Goods.Type.insert(label="My good type")
        self.incoming_loc = Wms.Location.insert(label="Incoming location")

        self.Operation = Wms.Operation
        self.Arrival = Wms.Operation.Arrival
        self.arrival = self.Arrival.insert(goods_type=goods_type,
                                           location=self.incoming_loc,
                                           state='planned',
                                           dt_execution=self.dt_test1,
                                           quantity=3)

        self.goods = Wms.Goods.insert(quantity=3,
                                      type=goods_type,
                                      location=self.incoming_loc,
                                      state='future',
                                      dt_from=self.dt_test1,
                                      reason=self.arrival)

    def test_op_err_instance(self):
        op_err = OperationError(self.arrival, "quantity is {qty}", qty=7)
        self.assertEqual(str(op_err),
                         "Model.Wms.Operation.Arrival: quantity is 7")
        repr_err = repr(op_err)
        self.assertTrue(repr_err.startswith(
            "OperationError(Model.Wms.Operation.Arrival, 'quantity is {qty}', "
        ))
        self.assertTrue('qty=7' in repr_err)
        self.assertTrue(
            "operation={op!r})".format(op=self.arrival) in repr_err)

    def test_op_err_cls(self):
        op_err = OperationError(self.Arrival, "quantity is {qty}", qty=7)
        self.assertEqual(str(op_err),
                         "Model.Wms.Operation.Arrival: quantity is 7")
        self.assertEqual(repr(op_err),
                         "OperationError(Model.Wms.Operation.Arrival, "
                         "'quantity is {qty}', qty=7)")

    def test_op_inputs_err_cls_missing_inputs(self):
        with self.assertRaises(ValueError):
            OperationInputsError(self.Arrival, "bogus")

    def test_op_wrong_state_instance_default_msg(self):
        self.goods.state = 'present'
        departure = self.Operation.Departure.create(input=self.goods,
                                                    quantity=3,
                                                    state='done')
        err = OperationInputWrongState(departure, self.goods, 'future')
        # Don't want to check the exact wording of the full fmt
        self.assertTrue(err.fmt.startswith, "Error for {operation}")
        kwargs = err.kwargs
        self.assertEqual(kwargs.get('record'), self.goods)
        self.assertEqual(kwargs.get('expected_state'), 'future')

        repr(err)
        str(err)
