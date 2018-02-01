# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok.tests.testcase import BlokTestCase


class TestUnpack(BlokTestCase):

    def setUp(self):
        Wms = self.registry.Wms
        self.Operation = Operation = Wms.Operation
        self.Unpack = Operation.Unpack
        self.Goods = Wms.Goods

        self.stock = Wms.Location.insert(label="Stock")

    def create_packs(self, type_behaviours=None):
        self.packed_goods_type = self.Goods.Type.insert(
            label="Pack",
            behaviours=type_behaviours)
        goods_type = self.Goods.Type.insert(label="My good type")

        self.arrival = self.Operation.Arrival.insert(
            goods_type=goods_type,
            location=self.stock,
            state='planned',
            quantity=3)

        self.packs = self.Goods.insert(quantity=5,
                                       type=self.packed_goods_type,
                                       location=self.stock,
                                       state='future',
                                       reason=self.arrival)

    def test_whole_done_one_unpacked_type(self):
        unpacked_type = self.Goods.Type.insert(label="Unpacked")
        self.create_packs(type_behaviours=dict(
            unpack=[(unpacked_type.id, 3)]))
        self.packs.update(state='present')
        unp = self.Unpack.create(quantity=5,
                                 state='done',
                                 goods=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        unpacked_goods = self.Goods.query().filter(
            self.Goods.type == unpacked_type).all()

        self.assertEqual(len(unpacked_goods), 1)
        unpacked_goods = unpacked_goods[0]
        self.assertEqual(unpacked_goods.quantity, 15)
        self.assertEqual(unpacked_goods.type, unpacked_type)
