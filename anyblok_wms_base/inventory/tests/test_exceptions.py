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
                          NodeChildrenStateError,
                          ActionInputsMissing,
                          )


class ExceptionTestCase(WmsTestCaseWithPhysObj):

    def setUp(self):
        super().setUp()
        self.Inventory = self.registry.Wms.Inventory

    def test_node_state(self):
        inventory = self.Inventory.create(location=self.stock)
        node = inventory.root
        exc = NodeStateError(node, "Something about Node (id={id}) "
                             "in state {state!r}")
        self.assertEqual(str(exc),
                         "Something about Node (id=%d) in state %r" % (
                             node.id, node.state))

    def test_node_children_state(self):
        inventory = self.Inventory.create(location=self.stock)
        root = inventory.root
        loc_a = self.insert_location("A", parent=self.stock)
        root.split()
        node = self.Inventory.Node.query().filter_by(location=loc_a).one()
        exc = NodeChildrenStateError(
            root, [node],
            "Children of (id={id}) states {children_states!r}")
        self.assert_singleton(exc.children_states.values(), value='draft')
        self.assertEqual(str(exc),
                         "Children of (id=%d) "
                         "states {%r: 'draft'}" % (root.id, str(node)))

    def test_action_inputs_missing(self):
        inventory = self.Inventory.create(location=self.stock)
        root = inventory.root
        loc_a = self.insert_location("A", parent=self.stock)
        action = self.Inventory.Action.insert(
            node=root, type='app', location=loc_a,
            physobj_type=self.physobj_type, quantity=3)

        exc = ActionInputsMissing(action, 2,
                                  "{action} got {nb_found}/{nb_expected}")
        self.assertEqual(str(exc), "%r got 2/3" % action)
