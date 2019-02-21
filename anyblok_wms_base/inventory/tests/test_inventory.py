# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCaseWithPhysObj
from ..exceptions import (NodeStateError,
                          )


class InventoryOrderTestCase(WmsTestCaseWithPhysObj):

    def setUp(self):
        super().setUp()
        self.Inventory = self.registry.Wms.Inventory

    def test_create(self):
        inv = self.Inventory.create(location=self.stock)
        root = inv.root
        self.assertIsInstance(root, self.Inventory.Node)
        self.assertEqual(root.location, self.stock)

    def test_reconcile_all(self):
        pot = self.physobj_type
        loc_a = self.insert_location("A", parent=self.stock)
        loc_aa = self.insert_location("AA", parent=loc_a)
        loc_ab = self.insert_location("AB", parent=loc_a)
        loc_b = self.insert_location("B", parent=self.stock)

        Arrival = self.Operation.Arrival
        Arrival.create(state='done', physobj_type=pot,
                       physobj_code='orig_aa', location=loc_aa)
        Arrival.create(state='done', physobj_type=pot,
                       physobj_code='orig_ab', location=loc_ab)

        inv = self.Inventory.create(location=self.stock)
        root = inv.root
        root.split()

        Node = self.Inventory.Node
        node_a = self.single_result(Node.query().filter_by(location=loc_a))
        node_b = self.single_result(Node.query().filter_by(location=loc_b))

        Action = self.Inventory.Action
        # normally, after computation, subnodes only have Teleportations
        # and all Apparitions and Disparitions are at the root Node,
        # This shouldn't be an issue for Inventory.reconcile_all()
        Action.insert(node=root, type='app', location=loc_b,
                      physobj_type=pot, physobj_code='appeared_b',
                      quantity=1)
        Action.insert(node=node_a, type='telep',
                      location=loc_ab, destination=loc_aa,
                      physobj_type=pot, physobj_code='orig_ab',
                      quantity=1)
        Action.insert(node=root, type='disp', location=loc_aa,
                      physobj_type=pot, physobj_code='orig_aa',
                      quantity=1)
        for node in (root, node_a, node_b):
            node.state = 'pushed'

        inv.reconcile_all()
        PhysObj, Avatar = self.PhysObj, self.Avatar

        present_avatars = (self.Avatar.query()
                           .join(PhysObj, PhysObj.id == Avatar.obj_id)
                           .filter(Avatar.state == 'present',
                                   PhysObj.type_id == pot.id)
                           .all())
        self.assertEqual({(av.location.code, av.obj.code)
                          for av in present_avatars},
                         {('AA', 'orig_ab'),
                          ('B', 'appeared_b'),
                          })

        for node in (root, node_a, node_b):
            self.assertEqual(node.state, 'reconciled')

    def test_reconcile_all_not_ready(self):
        inv = self.Inventory.create(location=self.stock)
        with self.assertRaises(NodeStateError) as arc:
            inv.reconcile_all()
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.node, inv.root)


del WmsTestCaseWithPhysObj
