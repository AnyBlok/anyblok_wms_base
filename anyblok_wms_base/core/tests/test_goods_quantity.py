# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCase


class TestQuantity(WmsTestCase):
    """Test quantity computation

    For now, in this class, only cases with no starting location are tested,
    because formerly the quantity computation was exposed as an instance method
    of Location, which now just calls on ``Wms.quantity()``, and whose tests
    cover the cases with starting location.
    """

    def setUp(self):
        super(TestQuantity, self).setUp()
        self.Avatar = self.Goods.Avatar

        self.goods_type = self.Goods.Type.insert(label="My goods",
                                                 code='MyGT')
        self.stock = self.insert_location('STK')
        self.arrival = self.Operation.Arrival.insert(
            goods_type=self.goods_type,
            location=self.stock,
            dt_execution=self.dt_test1,
            state='done')

        self.default_quantity_location = None

    def insert_goods(self, qty, state, dt_from, until=None, location=None):
        for _ in range(qty):
            self.Avatar.insert(
                goods=self.Goods.insert(type=self.goods_type),
                reason=self.arrival,
                location=self.stock if location is None else location,
                dt_from=dt_from,
                dt_until=until,
                state=state)

    def test_quantity_no_loc(self):
        # cases with a given location are for now treated in test_location
        self.insert_goods(2, 'present', self.dt_test1)
        self.insert_goods(1, 'present', self.dt_test2)
        self.insert_goods(4, 'future', self.dt_test3)
        self.insert_goods(2, 'past', self.dt_test1, until=self.dt_test2)

        self.assert_quantity(3)
        self.assert_quantity(3, goods_type=self.goods_type)
        self.assert_quantity(0, goods_type=self.Goods.Type.insert(code='other'))

        self.assert_quantity(7, additional_states=['future'],
                             at_datetime=self.dt_test3)

        self.assert_quantity(3, additional_states=['future'],
                             at_datetime=self.dt_test2)
        # the 'past' and 'present' ones were already there
        self.assert_quantity(4, additional_states=['past'],
                             at_datetime=self.dt_test1)
        # the 'past' one was not there anymore,
        # but the two 'present' ones had already arrived
        self.assert_quantity(3, additional_states=['past'],
                             at_datetime=self.dt_test2)

    def test_quantity_loc_tag(self):
        """No starting location, but filtering with location tags."""
        self.stock.container_tag = 'ok'
        sub = self.insert_location('sub', parent=self.stock)
        exc = self.insert_location('except', tag='nope', parent=self.stock)

        self.insert_goods(1, 'present', self.dt_test2, location=self.stock)
        self.insert_goods(1, 'present', self.dt_test2, location=sub)
        self.insert_goods(1, 'present', self.dt_test2, location=exc)
        self.assert_quantity(2, location_tag='ok')
        self.assert_quantity(1, location_tag='nope')
        self.assert_quantity(3)
