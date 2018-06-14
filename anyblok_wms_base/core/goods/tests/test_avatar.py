# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCaseWithGoods


class TestAvatar(WmsTestCaseWithGoods):

    def setUp(self):
        super(TestAvatar, self).setUp()
        self.Avatar = self.registry.Wms.Goods.Avatar

    def test_str(self):
        avatar, goods = self.avatar, self.goods
        gt = goods.type
        self.maxDiff = None

        # this below just to make sure. Actually, avatar.dt_from can be
        # expressed in a different time zone than the original because
        # of round trip with the database. This changes
        # repr() and str(), making the test dependent on the server timezone
        # but doesn't matter in truth.
        self.assertEqual(avatar.dt_from, self.dt_test1)

        self.assertEqual(
            repr(avatar),
            "Wms.Goods.Avatar(id=%d, "
            "goods=Wms.Goods(id=%d, "
            "type=Wms.Goods.Type(id=%d, code='MyGT')), "
            "state='future', "
            "location=Wms.Location("
            "id=%d, code=None, label='Incoming location'), "
            "dt_range=[%r, None])" % (
                avatar.id, goods.id, gt.id, self.incoming_loc.id,
                avatar.dt_from))

        self.assertEqual(
            str(avatar),
            "(id=%d, "
            "goods=(id=%d, type=(id=%d, code='MyGT')), "
            "state='future', "
            "location=(id=%d, code=None, label='Incoming location'), "
            "dt_range=[%s, None])" % (
                avatar.id, goods.id, gt.id, self.incoming_loc.id,
                avatar.dt_from))

    def test_get_property(self):
        avatar = self.avatar
        self.assertIsNone(avatar.get_property('foo'))
        self.goods.set_property('foo', [1])
        self.assertEqual(avatar.get_property('foo'), [1])
        self.assertEqual(avatar.get_property('bar', default='graal'), 'graal')


del WmsTestCaseWithGoods
