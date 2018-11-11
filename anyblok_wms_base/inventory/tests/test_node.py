# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCaseWithPhysObj


class InventoryNodeTestCase(WmsTestCaseWithPhysObj):

    def setUp(self):
        super().setUp()
        self.Inventory = self.registry.Wms.Inventory
        self.Order = self.Inventory.Order
        self.Node = self.Inventory.Node
        self.avatar.update(location=self.stock, state='present')

    def test_split(self):
        stock = self.stock
        order = self.Order.create(location=stock)
        node = order.root
        self.assertTrue(node.is_leaf)
        loc_a = self.insert_location("A", parent=stock)
        # to make things more interesting, let's use a sub container Type
        # in the current implementation, this exerts a recursive CTE
        loc_b = self.insert_location("B",
                                     parent=stock,
                                     location_type=self.PhysObj.Type.insert(
                                         code='SUBLOC', parent=stock.type))
        # check assumption: self.physobj is currently in stock as well
        self.assertEqual(self.avatar.location, stock)
        self.assertEqual(self.avatar.state, 'present')

        children = node.split()
        self.assertFalse(node.is_leaf)
        self.assertEqual(len(children), 2)

        # in particular, there's no child created for self.physobj
        self.assertEqual(set(children),
                         set(self.Node.query().filter_by(parent=node).all()))
        self.assertEqual(set(c.location for c in children),
                         {loc_a, loc_b})
        self.assertTrue(all(c.order == order for c in children))


del WmsTestCaseWithPhysObj
