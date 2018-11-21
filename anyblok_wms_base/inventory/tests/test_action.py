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

    def test_apply_app(self):
        pot = self.pot
        loc_a = self.loc_a
        action = self.Action.insert(
            node=self.node, type='app', location=loc_a,
            physobj_type=pot, physobj_code='from_action',
            physobj_properties=dict(qa='nok'),
            quantity=3)

        app = self.assert_singleton(action.apply())
        self.assertIsInstance(app, self.Operation.Apparition)
        self.assertEqual(app.inventory, self.inventory)
        self.assertEqual(app.quantity, 3)
        self.assertEqual(app.location, loc_a)
        self.assertEqual(app.physobj_type, pot)
        self.assertEqual(app.physobj_code, 'from_action')
        self.assertEqual(app.physobj_properties, dict(qa='nok'))
        self.assertEqual(app.state, 'done')
        # I don't see much value in checking that Apparition does its job

    def test_apply_telep(self):
        pot = self.pot
        loc_a, loc_b = self.loc_a, self.loc_b

        Arrival = self.Operation.Arrival
        po_fields = dict(physobj_type=pot, physobj_code='from_action',
                         physobj_properties=dict(qa='nok'))

        action = self.Action.insert(node=self.node, type='telep',
                                    location=loc_a, destination=loc_b,
                                    quantity=2, **po_fields)

        avatars = set(Arrival.create(state='done', location=loc_a,
                                     **po_fields).outcome
                      for i in range(2))

        ops = action.apply()

        self.assertEqual(set(op.input for op in ops), avatars)
        for op in ops:
            self.assertIsInstance(op, self.Operation.Teleportation)
            self.assertEqual(op.new_location, loc_b)
            self.assertEqual(op.state, 'done')
        # I don't see much value in checking that Teleportation does its job

    def test_apply_disp(self):
        pot = self.pot
        loc_a = self.loc_a

        Arrival = self.Operation.Arrival
        po_fields = dict(physobj_type=pot, physobj_code='from_action',
                         physobj_properties=dict(qa='nok'))

        action = self.Action.insert(node=self.node, type='disp',
                                    location=loc_a, quantity=3,
                                    **po_fields)

        avatars = set(Arrival.create(state='done', location=loc_a,
                                     **po_fields).outcome
                      for i in range(3))

        ops = action.apply()

        self.assertEqual(set(op.input for op in ops), avatars)
        for op in ops:
            self.assertIsInstance(op, self.Operation.Disparition)
            self.assertEqual(op.state, 'done')
        # I don't see much value in checking that Disparition does its job

    def test_choose_affected_not_enough(self):
        pot = self.pot
        loc_a = self.loc_a

        Arrival = self.Operation.Arrival
        po_fields = dict(physobj_type=pot, physobj_code='from_action',
                         physobj_properties=dict(qa='nok'))
        action = self.Action.insert(node=self.node, type='disp',
                                    location=loc_a, quantity=2, **po_fields)

        Arrival.create(state='done', location=loc_a, **po_fields)

        # TODO precise exc and test its attributes
        with self.assertRaises(ValueError):
            action.apply()


del SharedDataTestCase
