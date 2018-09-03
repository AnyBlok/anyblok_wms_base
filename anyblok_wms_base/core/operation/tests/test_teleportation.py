# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCaseWithGoods
from anyblok_wms_base.exceptions import (
    OperationIrreversibleError,
    OperationForbiddenState,
    OperationContainerExpected,
)


class TestTeleportation(WmsTestCaseWithGoods):

    def setUp(self):
        super(TestTeleportation, self).setUp()
        self.Teleportation = self.registry.Wms.Operation.Teleportation
        self.avatar.state = 'present'

    def test_create_done_irreversible_obliviate(self):
        avatar = self.avatar
        telep = self.Teleportation.create(state='done',
                                          dt_execution=self.dt_test2,
                                          new_location=self.stock,
                                          input=avatar)
        self.assertEqual(avatar.state, 'past')
        self.assertEqual(avatar.reason, telep)
        self.assertEqual(avatar.dt_until, self.dt_test2)

        outcome = self.assert_singleton(telep.outcomes)
        self.assertEqual(outcome.state, 'present')
        self.assertEqual(outcome.reason, telep)
        self.assertEqual(outcome.dt_from, self.dt_test2)
        self.assertEqual(outcome.location, self.stock)
        self.assertIsNone(outcome.dt_until)

        repr(telep)
        str(telep)

        with self.assertRaises(OperationIrreversibleError) as arc:
            telep.plan_revert()

        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.operation, telep)

        telep.obliviate()
        self.assertEqual(avatar.state, 'present')
        self.assertEqual(avatar.reason, self.arrival)
        self.assertIsNone(avatar.dt_until)
        self.assertEqual(
            self.Avatar.query().filter_by(goods=avatar.goods).count(), 1)

    def test_no_planned_state(self):
        avatar = self.avatar
        avatar.state = 'present'
        with self.assertRaises(OperationForbiddenState) as arc:
            self.Teleportation.create(state='planned',
                                      dt_execution=self.dt_test2,
                                      new_location=self.stock,
                                      input=avatar)

        exc = arc.exception
        repr(exc)
        str(exc)
        self.assertEqual(exc.kwargs.get('forbidden'), 'planned')

    def test_not_a_container(self):
        self.avatar.state = 'present'
        wrong_loc = self.Goods.insert(type=self.goods_type)
        with self.assertRaises(OperationContainerExpected) as arc:
            self.Teleportation.create(
                state='done',
                new_location=wrong_loc,
                input=self.avatar)
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['offender'], wrong_loc)


del WmsTestCaseWithGoods
