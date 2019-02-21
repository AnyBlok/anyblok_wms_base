# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
import random
from datetime import datetime
from anyblok.tests.testcase import SharedDataTestCase
from anyblok_wms_base.testing import WmsTestCase, UTC
from anyblok_wms_base.testing import skip_unless_bloks_installed
from ..exceptions import (ActionInputsMissing,
                          )


class InventoryActionTestCase(SharedDataTestCase, WmsTestCase):

    @classmethod
    def setUpSharedData(cls):
        cls.dt_test1 = datetime(2018, 1, 1, tzinfo=UTC)

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

    def test_repr(self):
        node = self.node
        pot = self.pot
        loc_a, loc_b = self.loc_a, self.loc_b
        Action = self.Action
        self.maxDiff = None
        self.assertEqual(
            repr(Action(node=node, type='app', location=loc_a,
                        physobj_type=pot, quantity=2)),
            "Wms.Inventory.Action(type='app', node=%r, "
            "location_code='A', quantity=2, "
            "physobj_type_code='TYPE1', "
            "physobj_code=None, physobj_properties=None)" % node)

        self.assertEqual(
            repr(Action(node=node, type='disp', location=loc_b,
                        physobj_type=pot, physobj_code='CS300', quantity=3)),
            "Wms.Inventory.Action(type='disp', node=%r, "
            "location_code='B', quantity=3, "
            "physobj_type_code='TYPE1', "
            "physobj_code='CS300', physobj_properties=None)" % node)

        self.assertEqual(
            repr(Action(node=node, type='telep', location=loc_b,
                        destination=loc_a,
                        physobj_type=pot, quantity=1)),
            "Wms.Inventory.Action(type='telep', node=%r, "
            "location_code='B', destination_code='A', quantity=1, "
            "physobj_type_code='TYPE1', "
            "physobj_code=None, physobj_properties=None)" % node)

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

        with self.assertRaises(ActionInputsMissing) as arc:
            action.apply()

        exc = arc.exception
        str(exc)
        str(arc)
        self.assertEqual(exc.action, action)
        self.assertEqual(exc.nb_found, 1)

    @skip_unless_bloks_installed('wms-reservation')
    def test_choose_affected_with_reserved(self):
        pot, loc_a = self.pot, self.loc_a
        Reservation = self.registry.Wms.Reservation
        po_loc = dict(physobj_type=pot, location=loc_a)
        Apparition = self.Operation.Apparition
        app = Apparition.create(quantity=3, state='done', **po_loc)

        outcomes = app.outcomes
        avatars = list(outcomes)
        # if avatars are in creation order, as long with phobjs and Reservation
        # Requests, then the test risks passing by coincidence, so we shuffle
        # them.
        # This means that reproduction of tests failure can need several runs
        # but that's acceptable.
        while avatars == outcomes:
            random.shuffle(avatars)

        requests = []
        for i in range(2):
            avatars[i].mark = 'resa%d' % i  # to ease debugging
            request = Reservation.Request.insert()
            requests.append(request)
            Reservation.insert(physobj=avatars[i].obj,
                               request_item=Reservation.RequestItem.insert(
                                   request=request,
                                   goods_type=pot,
                                   quantity=2))

        action = self.Action.insert(node=self.node, type='disp',
                                    quantity=1, **po_loc)
        # the first chosen obj is the unreserved one
        self.assert_singleton(action.choose_affected(), value=avatars[2])

        # if we have to break a reservation, it'd be the most recent one
        action.quantity = 2
        self.assertEqual(set(action.choose_affected()),
                         {avatars[1], avatars[2]})


del SharedDataTestCase
