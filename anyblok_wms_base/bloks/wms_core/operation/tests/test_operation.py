# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok.tests.testcase import BlokTestCase


class TestOperation(BlokTestCase):

    def test_history(self):
        Wms = self.registry.Wms
        Operation = Wms.Operation

        goods_type = Wms.Goods.Type.insert(label="My good type")
        incoming_loc = Wms.Location.insert(label="Incoming location")
        stock = Wms.Location.insert(label="Stock")

        arrival = Operation.Arrival.insert(goods_type=goods_type,
                                           location=incoming_loc,
                                           state='planned',
                                           quantity=3)

        goods = Wms.Goods.insert(quantity=3,
                                 type=goods_type,
                                 location=incoming_loc,
                                 state='future',
                                 reason=arrival)
        move = Operation.Move.insert(destination=stock,
                                     quantity=2,
                                     state='planned',
                                     goods=goods)
        move.follows.append(arrival)
        self.assertEqual(move.follows, [arrival])
