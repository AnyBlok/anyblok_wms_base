# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from decimal import Decimal as D

from anyblok_wms_base.testing import WmsTestCase
from anyblok.tests.testcase import BlokTestCase
from anyblok_wms_base.constants import (
    SPLIT_AGGREGATE_PHYSICAL_BEHAVIOUR
)


class TestPhysObj(WmsTestCase):

    def setUp(self):
        super(TestPhysObj, self).setUp()
        Wms = self.registry.Wms

        self.PhysObj = Wms.PhysObj
        self.Avatar = Wms.PhysObj.Avatar
        self.goods_type = self.PhysObj.Type.insert(label="My goods", code="MG")
        self.stock = self.insert_location('Stock')
        self.arrival = Wms.Operation.Arrival.insert(
            goods_type=self.goods_type,
            location=self.stock,
            dt_execution=self.dt_test1,
            state='done',
            quantity=1)

    def test_str(self):
        gt = self.goods_type
        goods = self.PhysObj.insert(type=gt, quantity=D('2.5'))
        self.assertEqual(repr(goods),
                         "Wms.PhysObj(id=%d, type="
                         "Wms.PhysObj.Type(id=%d, code='MG'), "
                         "quantity=Decimal('2.5'))" % (
                             goods.id, gt.id))
        self.assertEqual(str(goods),
                         "(id=%d, type="
                         "(id=%d, code='MG'), quantity=2.5)" % (
                             goods.id,
                             gt.id))


class TestPhysObjTypes(BlokTestCase):

    def setUp(self):
        self.PhysObjType = self.registry.Wms.PhysObj.Type

    def test_split_reversible(self):
        gt = self.PhysObjType(code='MG')
        self.assertTrue(gt.is_split_reversible())

        gt.behaviours = {SPLIT_AGGREGATE_PHYSICAL_BEHAVIOUR: True}
        self.assertFalse(gt.is_split_reversible())

        gt.behaviours['split'] = dict(reversible=True)
        self.assertTrue(gt.is_split_reversible())

    def test_aggregate_reversible(self):
        gt = self.PhysObjType(code='MG')
        self.assertTrue(gt.is_aggregate_reversible())

        gt.behaviours = {SPLIT_AGGREGATE_PHYSICAL_BEHAVIOUR: True}
        self.assertFalse(gt.is_aggregate_reversible())

        gt.behaviours['aggregate'] = dict(reversible=True)
        self.assertTrue(gt.is_aggregate_reversible())
