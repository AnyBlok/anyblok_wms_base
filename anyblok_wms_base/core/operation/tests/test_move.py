# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCaseWithPhysObj

from anyblok_wms_base.exceptions import (
    OperationError,
    OperationContainerExpected,
)


class TestMove(WmsTestCaseWithPhysObj):

    def setUp(self):
        super(TestMove, self).setUp()
        self.Move = self.Operation.Move
        self.avatar.dt_until = self.dt_test3

    def assertBackToBeginning(self):
        new_goods = self.single_result(self.Avatar.query())
        self.assertEqual(new_goods.location, self.incoming_loc)
        self.assertEqual(new_goods.state, 'present')
        self.assertEqual(new_goods.dt_from, self.dt_test1)
        self.assertEqual(new_goods.dt_until, self.dt_test3)
        # TODO also check that id did not change once we can make it True

    def test_whole_planned_execute(self):
        move = self.Move.create(destination=self.stock,
                                state='planned',
                                dt_execution=self.dt_test2,
                                input=self.avatar)
        self.assert_singleton(move.follows, value=self.arrival)
        self.assertEqual(move.input, self.avatar)
        self.avatar.update(state='present')

        move.execute()
        self.assertEqual(move.state, 'done')

        moved = self.assert_singleton(move.outcomes)
        self.assertEqual(moved.state, 'present')
        self.assertEqual(moved.location, self.stock)
        self.assertEqual(self.Avatar.query()
                         .filter(self.Avatar.location == self.incoming_loc,
                                 self.Avatar.state != 'past')
                         .count(),
                         0)

    def test_whole_done(self):
        self.avatar.update(state='present')
        move = self.Move.create(destination=self.stock,
                                state='done',
                                dt_execution=self.dt_test2,
                                input=self.avatar)
        self.assert_singleton(move.follows, value=self.arrival)

        after_move = move.outcome
        self.assertEqual(after_move.location, self.stock)
        self.assertEqual(after_move.state, 'present')

        not_moved = move.input
        self.assertEqual(not_moved.state, 'past')

    def test_whole_done_obliviate(self):
        self.avatar.state = 'present'
        move = self.Move.create(destination=self.stock,
                                state='done',
                                input=self.avatar)  # result already tested
        move.obliviate()
        self.assertBackToBeginning()

    def test_whole_planned_execute_obliviate(self):
        move = self.Move.create(destination=self.stock,
                                dt_execution=self.dt_test2,
                                state='planned',
                                input=self.avatar)
        self.avatar.update(state='present')
        move.execute()  # result already tested
        move.obliviate()
        self.assertBackToBeginning()

    def test_not_a_container(self):
        wrong_loc = self.PhysObj.insert(type=self.physobj_type)
        with self.assertRaises(OperationContainerExpected) as arc:
            self.Move.create(
                destination=wrong_loc,
                dt_execution=self.dt_test2,
                state='planned',
                input=self.avatar)
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['offender'], wrong_loc)

    def test_plan_for_outcomes_wrong_nb(self):
        with self.assertRaises(OperationError) as arc:
            self.Move.plan_for_outcomes([self.avatar],
                                        (), destination=self.stock)
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['outcomes'], ())
        self.assertEqual(exc.kwargs['nb_outcomes'], 0)

        # this would be very wrong, but what matters here is the length
        # of the 'outcomes' parameter
        with self.assertRaises(OperationError) as arc:
            self.Move.plan_for_outcomes([self.avatar],
                                        [1, 2], destination=self.stock)
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['outcomes'], [1, 2])
        self.assertEqual(exc.kwargs['nb_outcomes'], 2)


del WmsTestCaseWithPhysObj
