# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from datetime import datetime
from anyblok.blok import BlokManager
from anyblok.tests.testcase import BlokTestCase


class TestCore(BlokTestCase):

    def test_minimal(self):
        Wms = self.registry.Wms
        goods_type = Wms.Goods.Type.insert(label="My good type")
        self.assertEqual(goods_type.label, "My good type")

        loc = Wms.Location.insert(label="Root location")
        arrival = Wms.Operation.Arrival.insert(goods_type=goods_type,
                                               location=loc,
                                               dt_execution=datetime.now(),
                                               state='done')
        # basic test of polymorphism
        op = Wms.Operation.query().get(arrival.id)
        self.assertEqual(op, arrival)
        self.assertEqual(op.state, 'done')
        self.assertEqual(op.location, loc)

    def test_reload(self):
        import sys
        module_type = sys.__class__  # is there a simpler way ?

        def fake_reload(module):
            self.assertIsInstance(module, module_type)

        blok = BlokManager.get('wms-core')
        blok.reload_declaration_module(fake_reload)
