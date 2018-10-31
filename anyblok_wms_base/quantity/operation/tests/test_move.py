# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCaseWithPhysObj


class TestMove(WmsTestCaseWithPhysObj):

    arrival_kwargs = dict(quantity=3)

    def setUp(self):
        super(TestMove, self).setUp()
        self.avatar.dt_until = self.dt_test3
        self.Move = self.Operation.Move

    def test_partial_done(self):
        self.avatar.update(state='present')
        move = self.Move.create(destination=self.stock,
                                quantity=1,
                                state='done',
                                dt_execution=self.dt_test2,
                                input=self.avatar)
        split = self.assert_singleton(move.follows)
        self.assertEqual(split.type, 'wms_split')

        # the original has been thrown in the past by the split
        self.assertEqual(self.avatar.obj.quantity, 3)
        self.assertEqual(self.avatar.state, 'past')
        self.assertEqual(self.avatar.dt_from, self.dt_test1)
        self.assertEqual(self.avatar.dt_until, self.dt_test2)

        not_moved = self.assert_singleton(split.leaf_outcomes())
        self.assertEqual(not_moved.obj.quantity, 2)

        after_move = self.assert_singleton(move.outcomes)
        self.assertEqual(after_move.obj.quantity, 1)
        self.assertEqual(after_move.dt_from, self.dt_test2)
        self.assertEqual(after_move.dt_until, self.dt_test3)
        self.assertEqual(after_move.location, self.stock)

    def test_partial_planned_execute(self):
        move = self.Move.create(destination=self.stock,
                                quantity=1,
                                state='planned',
                                dt_execution=self.dt_test2,
                                input=self.avatar)
        split = self.assert_singleton(move.follows)
        self.assertEqual(split.type, 'wms_split')

        self.avatar.state = 'present'
        self.registry.flush()
        move.execute(dt_execution=self.dt_test2)

        # the original has been thrown in the past by the split
        self.assertEqual(self.avatar.obj.quantity, 3)
        self.assertEqual(self.avatar.state, 'past')
        self.assertEqual(self.avatar.dt_from, self.dt_test1)
        self.assertEqual(self.avatar.dt_until, self.dt_test2)

        not_moved = self.assert_singleton(split.leaf_outcomes())
        self.assertEqual(not_moved.obj.quantity, 2)

        after_move = self.assert_singleton(move.outcomes)
        self.assertEqual(after_move.obj.quantity, 1)
        self.assertEqual(after_move.location, self.stock)
        self.assertEqual(after_move.dt_from, self.dt_test2)
        self.assertEqual(after_move.dt_until, self.dt_test3)
        self.assertEqual(after_move.state, 'present')


del WmsTestCaseWithPhysObj
