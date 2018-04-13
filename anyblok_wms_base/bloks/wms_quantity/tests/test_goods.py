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


class TestGoods(WmsTestCase):

    def setUp(self):
        super(TestGoods, self).setUp()
        Wms = self.registry.Wms

        self.Goods = Wms.Goods
        self.Avatar = Wms.Goods.Avatar
        self.goods_type = self.Goods.Type.insert(label="My goods", code="MG")
        self.stock = Wms.Location.insert(label="Stock")
        self.arrival = Wms.Operation.Arrival.insert(
            goods_type=self.goods_type,
            location=self.stock,
            dt_execution=self.dt_test1,
            state='done',
            quantity=1)

    def test_str(self):
        gt = self.goods_type
        goods = self.Goods.insert(type=gt, quantity=D('2.5'))
        self.assertEqual(repr(goods),
                         "Wms.Goods(id=%d, type="
                         "Wms.Goods.Type(id=%d, code='MG'), "
                         "quantity=Decimal('2.5'))" % (
                             goods.id, gt.id))
        self.assertEqual(str(goods),
                         "(id=%d, type="
                         "(id=%d, code='MG'), quantity=2.5)" % (
                             goods.id,
                             gt.id))
