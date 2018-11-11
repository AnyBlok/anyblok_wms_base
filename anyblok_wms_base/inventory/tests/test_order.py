# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCase


class InventoryOrderTestCase(WmsTestCase):

    def setUp(self):
        self.Inventory = self.registry.Wms.Inventory
        self.Order = self.Inventory.Order
        self.create_location_type()
        self.stock = self.insert_location("STOCK")

    def test_create(self):
        order = self.Order.create(location=self.stock)
        root = order.root
        self.assertIsInstance(root, self.Inventory.Node)
        self.assertEqual(root.location, self.stock)
