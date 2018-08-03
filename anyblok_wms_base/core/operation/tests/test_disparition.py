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
)


class TestDisparition(WmsTestCaseWithGoods):

    def setUp(self):
        super(TestDisparition, self).setUp()
        self.Disparition = self.registry.Wms.Operation.Disparition

    def test_create_done_irreversible_obliviate(self):
        avatar = self.avatar
        avatar.state = 'present'
        disp = self.Disparition.create(state='done',
                                       dt_execution=self.dt_test2,
                                       input=avatar)
        self.assertEqual(len(disp.outcomes), 0)
        self.assertEqual(avatar.state, 'past')
        self.assertEqual(avatar.reason, disp)
        self.assertEqual(avatar.dt_until, self.dt_test2)
        self.assertIsNone(self.Avatar.query().filter(
            self.Avatar.state != 'past').first())

        repr(disp)
        str(disp)

        with self.assertRaises(OperationIrreversibleError) as arc:
            disp.plan_revert()

        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.operation, disp)

        disp.obliviate()
        self.assertEqual(avatar.state, 'present')
        self.assertEqual(avatar.reason, self.arrival)
        self.assertIsNone(avatar.dt_until)

    def test_no_planned_state(self):
        avatar = self.avatar
        avatar.state = 'present'
        with self.assertRaises(OperationForbiddenState) as arc:
            self.Disparition.create(state='planned',
                                    dt_execution=self.dt_test2,
                                    input=avatar)

        exc = arc.exception
        repr(exc)
        str(exc)
        self.assertEqual(exc.kwargs.get('forbidden'), 'planned')


del WmsTestCaseWithGoods
