# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from datetime import datetime
from anyblok.tests.testcase import SharedDataTestCase
from anyblok_wms_base.testing import WmsTestCase, FixedOffsetTimezone


class InventoryActionTestCase(SharedDataTestCase, WmsTestCase):

    @classmethod
    def setUpSharedData(cls):
        tz = cls.tz = FixedOffsetTimezone(0)
        cls.dt_test1 = datetime(2018, 1, 1, tzinfo=tz)

        cls.create_location_type()
        loc_root = cls.loc_root = cls.cls_insert_location('ROOT')
        cls.loc_a = cls.cls_insert_location("A", parent=loc_root)
        cls.loc_b = cls.cls_insert_location("B", parent=loc_root)

        cls.Inventory = cls.registry.Wms.Inventory
        cls.inventory = cls.Inventory.create(location=loc_root)
        cls.node = cls.inventory.root

        cls.Action = cls.Inventory.Action
        cls.pot = cls.PhysObj.Type.insert(code='TYPE1')
        cls.pot2 = cls.PhysObj.Type.insert(code='TYPE2')

    def node_actions(self):
        return {(a.type, a.location, a.destination,
                 a.physobj_type, a.physobj_code, a.quantity)
                for a in self.Action.query().filter_by(node=self.node).all()}

    def test_simplify_1(self):
        node = self.node
        pot = self.pot
        loc_a, loc_b = self.loc_a, self.loc_b
        self.Action.insert(node=node, type='app', location=loc_a,
                           physobj_type=pot, quantity=2)
        self.Action.insert(node=node, type='disp', location=loc_b,
                           physobj_type=pot, quantity=3)
        self.Action.simplify(node)

        self.assertEqual(self.node_actions(),
                         {('telep', loc_b, loc_a, pot, None, 2),
                          ('disp', loc_b, None, pot, None, 1),
                          })

    def test_simplify_2(self):
        node = self.node
        pot = self.pot
        loc_a, loc_b = self.loc_a, self.loc_b
        self.Action.insert(node=node, type='app', location=loc_a,
                           physobj_type=pot, quantity=3)
        self.Action.insert(node=node, type='disp', location=loc_b,
                           physobj_type=pot, quantity=2)
        self.Action.simplify(node)

        self.assertEqual(self.node_actions(),
                         {('telep', loc_b, loc_a, pot, None, 2),
                          ('app', loc_a, None, pot, None, 1),
                          })

    def test_simplify_3(self):
        node = self.node
        pot = self.pot
        loc_a, loc_b = self.loc_a, self.loc_b
        self.Action.insert(node=node, type='app', location=loc_a,
                           physobj_type=pot, quantity=3)
        self.Action.insert(node=node, type='disp', location=loc_b,
                           physobj_type=pot, quantity=3)
        self.Action.simplify(node)

        self.assert_singleton(self.node_actions(),
                              value=('telep', loc_b, loc_a, pot, None, 3))

    def check_simplify_non_matching_codes(self, code1, code2):
        node = self.node
        pot = self.pot
        loc_a, loc_b = self.loc_a, self.loc_b
        Action = self.Action
        actions = {Action.insert(node=node, type='app', location=loc_a,
                                 physobj_type=pot, physobj_code=code1,
                                 quantity=3),
                   Action.insert(node=node, type='disp', location=loc_b,
                                 physobj_type=pot, physobj_code=code2,
                                 quantity=2)}
        self.Action.simplify(node)
        self.assertEqual(set(self.Action.query().all()), actions)

    def test_simplify_non_matching_codes1(self):
        self.check_simplify_non_matching_codes('foo', 'bar')

    def test_simplify_non_matching_codes2(self):
        self.check_simplify_non_matching_codes('foo', None)

    def test_simplify_non_matching_codes3(self):
        self.check_simplify_non_matching_codes(None, 'bar')


del SharedDataTestCase
