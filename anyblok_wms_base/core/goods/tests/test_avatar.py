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
        self.assertEqual(
            repr(avatar),
            "Wms.Goods.Avatar(id=%d, "
            "goods=Wms.Goods(id=%d, type=Wms.Goods.Type(id=%d, code='MyGT')), "
            "state='future', "
            "location=Wms.Location("
            "id=%d, code=None, label='Incoming location'), "
            "dt_range=[datetime.datetime(2018, 1, 1, 1, 0, "
            "tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=60, name=None)), "
            "None)" % (
                avatar.id, goods.id, gt.id, self.incoming_loc.id))

        self.assertEqual(
            str(avatar),
            "(id=%d, "
            "goods=(id=%d, type=(id=%d, code='MyGT')), "
            "state='future', "
            "location=(id=%d, code=None, label='Incoming location'), "
            "dt_range=[2018-01-01 01:00:00+01:00, None)" % (
                avatar.id, goods.id, gt.id, self.incoming_loc.id))


del WmsTestCaseWithGoods
