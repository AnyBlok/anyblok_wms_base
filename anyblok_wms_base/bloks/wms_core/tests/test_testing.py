# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCaseWithGoods


class TestWmsTestCase(WmsTestCaseWithGoods):

    def test_sorted_props(self):
        avatar = self.avatar
        goods = avatar.goods
        goods.set_property('a', 3)
        goods.set_property('c', 'ok')
        for rec in (goods, avatar):
            # the batch property is a field-based one, therefore always
            # present
            self.assertEqual(self.sorted_props(rec),
                             (('a', 3), ('batch', None), ('c', 'ok')))
        with self.assertRaises(self.failureException):
            self.sorted_props(goods.type)
