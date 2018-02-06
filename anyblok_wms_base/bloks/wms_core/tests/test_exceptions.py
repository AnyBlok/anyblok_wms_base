# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok.tests.testcase import BlokTestCase
from anyblok_wms_base.exceptions import OperationError


class TestOperationError(BlokTestCase):

    def setUp(self):
        Wms = self.registry.Wms
        goods_type = Wms.Goods.Type.insert(label="My good type")
        self.incoming_loc = Wms.Location.insert(label="Incoming location")

        self.Arrival = Wms.Operation.Arrival
        self.arrival = self.Arrival.insert(goods_type=goods_type,
                                           location=self.incoming_loc,
                                           state='planned',
                                           quantity=3)

        self.goods = Wms.Goods.insert(quantity=3,
                                      type=goods_type,
                                      location=self.incoming_loc,
                                      state='future',
                                      reason=self.arrival)

    def test_op_err_instance(self):
        op_err = OperationError(self.arrival, "quantity is {qty}", qty=7)
        self.assertEqual(str(op_err),
                         "Model.Wms.Operation.Arrival: quantity is 7")
        self.assertEqual(repr(op_err),
                         "OperationError(Model.Wms.Operation.Arrival, "
                         "'quantity is {qty}', qty=7)")

    def test_op_err_cls(self):
        op_err = OperationError(self.Arrival, "quantity is {qty}", qty=7)
        self.assertEqual(str(op_err),
                         "Model.Wms.Operation.Arrival: quantity is 7")
        self.assertEqual(repr(op_err),
                         "OperationError(Model.Wms.Operation.Arrival, "
                         "'quantity is {qty}', qty=7)")
