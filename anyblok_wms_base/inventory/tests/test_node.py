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
        self.Node = self.Inventory.Node
        self.Line = self.Inventory.Line
        self.Action = self.Inventory.Action
        self.avatar.update(location=self.stock, state='present')

    def test_split(self):
        stock = self.stock
        inventory = self.Inventory.create(location=stock)
        node = inventory.root
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
        self.assertTrue(all(c.inventory == inventory for c in children))

    def test_compute_actions_not_enough_phobjs(self):
        inventory = self.Inventory.create(location=self.stock)
        node = inventory.root
        node.state = 'full'
        self.Line.insert(node=node,
                         location=self.stock,
                         type=self.physobj.type,
                         quantity=2)

        node.compute_actions()
        action = self.single_result(self.Action.query().filter_by(node=node))
        self.assertEqual(action.type, 'app')

        self.assertEqual(action.location, self.stock)
        self.assertEqual(action.physobj_type, self.physobj.type)
        self.assertEqual(action.quantity, 1)

        self.assertIsNone(action.physobj_code)
        self.assertIsNone(action.physobj_properties)

    def test_compute_actions_too_many_phobjs(self):
        inventory = self.Inventory.create(location=self.stock)
        node = inventory.root
        node.state = 'full'
        # of course, in real life it's more probable we wouldn't have
        # a line at all, but there's no real value to bother creating
        # a new physobj to compare 1 and 2 instead of 0 and 1
        self.Line.insert(node=node,
                         location=self.stock,
                         type=self.physobj.type,
                         quantity=0)

        node.compute_actions()
        action = self.single_result(self.Action.query().filter_by(node=node))
        self.assertEqual(action.type, 'disp')

        self.assertEqual(action.location, self.stock)
        self.assertEqual(action.physobj_type, self.physobj.type)
        self.assertEqual(action.quantity, 1)

        self.assertIsNone(action.physobj_code)
        self.assertIsNone(action.physobj_properties)

    def test_compute_actions_all_matching(self):
        inventory = self.Inventory.create(location=self.stock)
        node = inventory.root
        node.state = 'full'
        node_actions_q = self.Action.query().filter_by(node=node)

        self.Line.insert(node=node,
                         location=self.stock,
                         type=self.physobj.type,
                         quantity=1)
        node.compute_actions()
        self.assertEqual(node_actions_q.count(), 0)
        self.assertEqual(node.state, 'computed')

        self.Action.insert(type='app',
                           node=node,
                           location=self.stock,
                           physobj_type=self.physobj.type,
                           quantity=3)
        node.compute_actions(recompute=True)
        self.assertEqual(node_actions_q.count(), 0)
        self.assertEqual(node.state, 'computed')

    def test_compute_actions_wrong_phobj_code(self):
        inventory = self.Inventory.create(location=self.stock)
        node = inventory.root
        node.state = 'full'
        line = self.Line.insert(node=node,
                                location=self.stock,
                                type=self.physobj.type,
                                quantity=1,
                                code='Not on self.physobj!')

        node.compute_actions()
        actions = (self.Action.query()
                   .filter_by(node=node)
                   .order_by(self.Action.type)
                   .all())

        # it boils down to an Apparition and a Disparition at the same place

        for action in actions:
            self.assertEqual(action.location, self.stock)
            self.assertEqual(action.physobj_type, self.physobj.type)
            self.assertEqual(action.quantity, 1)
            self.assertIsNone(action.physobj_properties)

        app, disp = actions
        self.assertEqual(app.type, 'app')
        self.assertEqual(app.physobj_code, line.code)
        self.assertEqual(disp.type, 'disp')
        self.assertIsNone(disp.physobj_code)

    def test_compute_actions_avatar_elsewhere(self):
        inventory = self.Inventory.create(location=self.stock)
        node = inventory.root
        node.state = 'full'
        self.avatar.location = self.incoming_loc
        self.Line.insert(node=node,
                         location=self.stock,
                         type=self.physobj.type,
                         quantity=1)

        node.compute_actions()

        action = self.single_result(self.Action.query().filter_by(node=node))
        self.assertEqual(action.type, 'app')

        self.assertEqual(action.location, self.stock)
        self.assertEqual(action.physobj_type, self.physobj.type)
        self.assertEqual(action.quantity, 1)

        self.assertIsNone(action.physobj_code)
        self.assertIsNone(action.physobj_properties)

    def test_compute_actions_missing_line(self):
        inventory = self.Inventory.create(location=self.stock)
        node = inventory.root
        node.state = 'full'
        node.compute_actions()

        action = self.single_result(self.Action.query().filter_by(node=node))
        self.assertEqual(action.type, 'disp')

        self.assertEqual(action.location, self.stock)
        self.assertEqual(action.physobj_type, self.physobj.type)
        self.assertEqual(action.quantity, 1)

        self.assertIsNone(action.physobj_code)
        self.assertIsNone(action.physobj_properties)

    def test_compute_actions_wrong_states(self):
        inventory = self.Inventory.create(location=self.stock)
        node = inventory.root
        with self.assertRaises(ValueError):
            node.compute_actions()

        node.state = 'reconciled'
        with self.assertRaises(ValueError):
            node.compute_actions()


del WmsTestCaseWithPhysObj
