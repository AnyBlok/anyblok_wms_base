# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
import warnings
from anyblok_wms_base.testing import WmsTestCaseWithPhysObj
from anyblok_wms_base.constants import EMPTY_TIMESPAN
from anyblok_wms_base.dbapi import TimeSpan


class TestAvatar(WmsTestCaseWithPhysObj):

    def setUp(self):
        super(TestAvatar, self).setUp()
        self.Avatar = self.registry.Wms.PhysObj.Avatar

    def test_str(self):
        avatar, goods = self.avatar, self.physobj
        self.maxDiff = None

        # this below just to make sure. Actually, avatar.dt_from can be
        # expressed in a different time zone than the original because
        # of round trip with the database. This changes
        # repr() and str(), making the test dependent on the server timezone
        # but doesn't matter in truth.
        self.assertEqual(avatar.dt_from, self.dt_test1)

        self.assertEqual(
            repr(avatar),
            "Wms.PhysObj.Avatar(id=%d, obj=%r, state='future', "
            "location=%r, dt_range=[%r, None])" % (
                avatar.id, goods, self.incoming_loc, avatar.dt_from))

        self.assertEqual(
            str(avatar),
            "(id=%d, obj=%s, state='future', location=%s, "
            "dt_range=[%s, None])" % (
                avatar.id, goods, self.incoming_loc, avatar.dt_from))

    def test_compat_dt_from(self):
        avatar = self.avatar

        self.assertEqual(avatar.dt_from, self.dt_test1)
        avatar.dt_from = self.dt_test2
        self.registry.flush()
        avatar.expire()

        self.assertEqual(avatar.dt_from, self.dt_test2)

        avatar.timespan = EMPTY_TIMESPAN
        self.registry.flush()
        avatar.expire()

        avatar.dt_from = self.dt_test3
        self.assertEqual(avatar.dt_from, self.dt_test3)
        self.registry.flush()
        avatar.expire()

        self.assertEqual(avatar.dt_from, self.dt_test3)

    def test_compat_dt_until(self):
        avatar = self.avatar

        self.assertEqual(avatar.dt_until, None)
        avatar.dt_until = self.dt_test2
        self.registry.flush()
        avatar.expire()

        self.assertEqual(avatar.dt_until, self.dt_test2)

        avatar.timespan = EMPTY_TIMESPAN
        self.registry.flush()
        avatar.expire()

        with self.assertRaises(RuntimeError):
            avatar.dt_until = self.dt_test3

    def test_compat_dt_until_None(self):
        # during instantiation with dt_from, dt_until
        # kwargs, it happens that dt_until is set first
        avatar = self.avatar
        avatar.timespan = None
        avatar.dt_until = self.dt_test2
        self.assertIsNone(avatar.dt_from)
        # inclusivity of `None` lower bound doesn't make
        # much sense but it is useful once a true value is
        # set (None lower bounds in AWB are or should be
        # prohibited anyway)
        avatar.dt_from = self.dt_test1
        # let's make a round trip
        self.registry.flush()
        avatar.expire
        self.assertEqual(self.avatar.timespan,
                         TimeSpan(lower=self.dt_test1,
                                  upper=self.dt_test2,
                                  bounds='[)'))

    def test_get_property(self):
        avatar = self.avatar
        self.assertIsNone(avatar.get_property('foo'))
        self.physobj.set_property('foo', [1])
        self.assertEqual(avatar.get_property('foo'), [1])
        self.assertEqual(avatar.get_property('bar', default='graal'), 'graal')

    def test_compatibility_goods_field(self):
        """Test compatibility function field for the rename goods->obj.

        To be removed together with that function field once the deprecation
        has expired.
        """
        avatar = self.avatar
        phobj = avatar.obj

        def assert_warnings_goods_deprecation(got_warnings):
            self.assert_warnings_deprecation(
                got_warnings, "'goods'", "rename to 'obj'")

        with warnings.catch_warnings(record=True) as got:
            # reading
            self.assertEqual(avatar.goods, phobj)
        assert_warnings_goods_deprecation(got)

        with warnings.catch_warnings(record=True) as got:
            # writing
            avatar.dt_until = self.dt_test2  # avoid overlap
            self.Avatar.insert(goods=phobj,
                               state='present',
                               dt_from=self.dt_test2,
                               dt_until=None,
                               outcome_of=avatar.outcome_of,
                               location=avatar.location)
        assert_warnings_goods_deprecation(got)

        with warnings.catch_warnings(record=True) as got:
            # querying
            self.assertEqual(self.Avatar.query().filter_by(goods=phobj).count(),
                             2)
        assert_warnings_goods_deprecation(got)

    def test_pysobj_current_avatar(self):
        avatar = self.avatar
        # just to make sure
        self.assertEqual(avatar.state, 'future')
        phobj = avatar.obj

        self.assertIsNone(phobj.current_avatar())

        avatar.state = 'present'
        self.assertEqual(phobj.current_avatar(), avatar)

        avatar.state = 'past'
        self.assertIsNone(phobj.current_avatar())

    def test_pysobj_eventual_avatar(self):
        avatar = self.avatar
        # just to make sure
        self.assertEqual(avatar.state, 'future')
        phobj = avatar.obj

        self.assertEqual(phobj.eventual_avatar(), avatar)

        avatar.state = 'present'
        self.assertEqual(phobj.eventual_avatar(), avatar)

        avatar.state = 'past'
        self.assertIsNone(phobj.eventual_avatar())

    def test_pysobj_eventual_avatar_departure(self):
        """If the PhysObj is planned to leave, eventual_avatar() should be None
        """

        avatar = self.avatar
        # just to make sure
        self.assertEqual(avatar.state, 'future')
        phobj = avatar.obj

        self.Operation.Departure.create(input=avatar)
        self.assertIsNone(phobj.eventual_avatar())


del WmsTestCaseWithPhysObj
