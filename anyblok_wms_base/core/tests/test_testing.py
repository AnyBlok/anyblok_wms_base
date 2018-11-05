# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCaseWithPhysObj


class TestWmsTestCase(WmsTestCaseWithPhysObj):

    def test_sorted_props(self):
        avatar = self.avatar
        goods = avatar.obj
        goods.set_property('a', 3)
        goods.set_property('c', 'ok')
        for rec in (goods, avatar):
            # the batch property is a field-based one, therefore always
            # present
            self.assertEqual(self.sorted_props(rec),
                             (('a', 3), ('batch', None), ('c', 'ok')))
        with self.assertRaises(self.failureException):
            self.sorted_props(goods.type)

    def test_cls_insert_location(self):
        loc = self.cls_insert_location('other', parent=self.stock)
        av = self.assert_singleton(
            self.Avatar.query().filter_by(obj=loc).all())
        self.assertEqual(av.dt_from, self.dt_test1)

    def test_assert_quantity(self):
        self.assert_quantity(0, physobj_type=self.physobj_type)
        self.assert_quantity(1, physobj_type=self.physobj_type,
                             additional_states=['future'],
                             at_datetime=self.dt_test3)

    def test_assert_quantity_default_type(self):
        self.assert_quantity(1, additional_states=['future'],
                             at_datetime=self.dt_test3)

    def test_assert_quantity_api_compat(self):
        self.assert_quantity(1, goods_type=self.physobj_type,
                             additional_states=['future'],
                             at_datetime=self.dt_test3)


del WmsTestCaseWithPhysObj
