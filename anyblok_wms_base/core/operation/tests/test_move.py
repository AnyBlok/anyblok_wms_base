# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCaseWithGoods


class TestMove(WmsTestCaseWithGoods):

    def setUp(self):
        super(TestMove, self).setUp()
        Wms = self.registry.Wms
        Operation = Wms.Operation
        self.stock = Wms.Location.insert(label="Stock")

        self.avatar.dt_until = self.dt_test3
        self.Move = Operation.Move

    def assertBackToBeginning(self):
        new_goods = self.single_result(self.Avatar.query())
        self.assertEqual(new_goods.location, self.incoming_loc)
        self.assertEqual(new_goods.state, 'present')
        self.assertEqual(new_goods.dt_from, self.dt_test1)
        self.assertEqual(new_goods.dt_until, self.dt_test3)
        self.assertEqual(new_goods.reason, self.arrival)
        # TODO also check that id did not change once we can make it True

    def test_whole_planned_execute(self):
        move = self.Move.create(destination=self.stock,
                                state='planned',
                                dt_execution=self.dt_test2,
                                input=self.avatar)
        self.assertEqual(move.follows, [self.arrival])
        self.assertEqual(move.input, self.avatar)
        self.avatar.update(state='present')

        move.execute()
        self.assertEqual(move.state, 'done')
        self.assertEqual(self.avatar.reason, move)

        moved = self.assert_singleton(move.outcomes)
        self.assertEqual(moved.state, 'present')
        self.assertEqual(moved.reason, move)
        self.assertEqual(moved.location, self.stock)
        self.assertEqual(self.Avatar.query().filter(
            self.Avatar.location == self.incoming_loc,
            self.Avatar.state != 'past').count(), 0)

    def test_whole_done(self):
        self.avatar.update(state='present')
        move = self.Move.create(destination=self.stock,
                                state='done',
                                dt_execution=self.dt_test2,
                                input=self.avatar)
        self.assertEqual(move.follows, [self.arrival])

        after_move = move.outcomes[0]
        self.assertEqual(after_move.location, self.stock)
        self.assertEqual(after_move.state, 'present')
        self.assertEqual(after_move.reason, move)

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
