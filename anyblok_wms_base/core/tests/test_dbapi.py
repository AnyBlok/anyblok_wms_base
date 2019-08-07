# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.dbapi import (
    TimeSpan,
    DATE_TIME_INFINITY,
    )
from anyblok_wms_base.testing import WmsTestCaseWithPhysObj


class TestDbAPI(WmsTestCaseWithPhysObj):

    def test_dt_infinity_scalar(self):
        op = self.arrival
        op.dt_execution = DATE_TIME_INFINITY
        self.registry.flush()
        op.refresh()
        self.assertEqual(op.dt_execution, DATE_TIME_INFINITY)

    def test_dt_infinity_range(self):
        av = self.avatar

        av.timespan = TimeSpan(lower=self.dt_test1,
                               upper=DATE_TIME_INFINITY,
                               bounds='[)')
        self.registry.flush()
        av.refresh()

        self.assertEqual(av.timespan.upper, DATE_TIME_INFINITY)
        self.assertTrue(self.dt_test2 in av.timespan)

        av.timespan = TimeSpan(lower=DATE_TIME_INFINITY,
                               upper=DATE_TIME_INFINITY,
                               bounds='[)')
        self.registry.flush()
        av.refresh()

        self.assertTrue(av.timespan.isempty)
        self.assertFalse(DATE_TIME_INFINITY in av.timespan)

        av.timespan = TimeSpan(lower=DATE_TIME_INFINITY,
                               upper=DATE_TIME_INFINITY,
                               bounds='[]')
        self.registry.flush()
        av.refresh()

        self.assertEqual(av.timespan.upper, DATE_TIME_INFINITY)
        self.assertEqual(av.timespan.lower, DATE_TIME_INFINITY)
        self.assertTrue(DATE_TIME_INFINITY in av.timespan)


del WmsTestCaseWithPhysObj
