# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCase
from anyblok_wms_base.constants import DATE_TIME_INFINITY


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
        avatars = []
        for _ in range(qty):
            avatars.append(self.Avatar.insert(
                goods=self.Goods.insert(type=self.goods_type),
                reason=self.arrival,
                location=self.stock if location is None else location,
                dt_from=dt_from,
                dt_until=until,
                state=state)
            )
        return avatars

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

    def test_quantity_no_recurse(self):
        # cases with a given location are for now treated in test_location
        sub = self.insert_location('sub', parent=self.stock)
        self.insert_goods(2, 'present', self.dt_test1, location=sub)
        self.insert_goods(1, 'present', self.dt_test1, location=self.stock)

        self.assert_quantity(1, goods_type=self.goods_type,
                             location=self.stock,
                             location_recurse=False)
        self.assert_quantity(2, goods_type=self.goods_type,
                             location=sub,
                             location_recurse=False)

    def test_dt_quantity_moved_loc(self):
        """Test quantity queries with Goods in a location that moves."""
        loc = self.insert_location('sub', parent=self.stock)
        loc_av = self.Avatar.query().filter_by(goods=loc).one()
        other = self.insert_location('other')
        self.insert_goods(3, 'present', self.dt_test1, location=loc)
        loc_move = self.Operation.Move.create(input=loc_av,
                                              destination=other,
                                              state='planned',
                                              dt_execution=self.dt_test2)
        for dt in (self.dt_test2, self.dt_test3, DATE_TIME_INFINITY):
            self.assert_quantity(0,
                                 additional_states=['future'],
                                 location=self.stock,
                                 at_datetime=dt)
            self.assert_quantity(3,
                                 additional_states=['future'],
                                 location=other,
                                 at_datetime=dt)

        loc_move.execute(dt_execution=self.dt_test2)

        self.assert_quantity(3,
                             additional_states=['past'],
                             location=self.stock,
                             at_datetime=self.dt_test1)
        self.assert_quantity(0,
                             additional_states=['past'],
                             location=other,
                             at_datetime=self.dt_test1)

        for dt in (self.dt_test2, self.dt_test3, DATE_TIME_INFINITY):
            self.assert_quantity(0,
                                 additional_states=['past'],
                                 location=self.stock,
                                 at_datetime=dt)
            self.assert_quantity(3,
                                 additional_states=['past'],
                                 location=other,
                                 at_datetime=dt)

    def test_dt_quantity_moved_loc_and_goods(self):
        """Test quantity queries with both Goods and locations moving."""
        loc = self.insert_location('sub', parent=self.stock)
        loc_av = self.Avatar.query().filter_by(goods=loc).one()
        other = self.insert_location('other')
        avatars = self.insert_goods(3, 'present', self.dt_test1)
        goods_move = self.Operation.Move.create(input=avatars[0],
                                                destination=loc,
                                                state='planned',
                                                dt_execution=self.dt_test2)
        loc_move = self.Operation.Move.create(input=loc_av,
                                              destination=other,
                                              state='planned',
                                              dt_execution=self.dt_test3)

        self.assert_quantity(3,
                             additional_states=['future'],
                             location=self.stock,
                             at_datetime=self.dt_test2)
        self.assert_quantity(0,
                             additional_states=['future'],
                             location=other,
                             at_datetime=self.dt_test2)
        for dt in (self.dt_test3, DATE_TIME_INFINITY):
            self.assert_quantity(2,
                                 additional_states=['future'],
                                 location=self.stock,
                                 at_datetime=dt)
            self.assert_quantity(1,
                                 additional_states=['future'],
                                 location=other,
                                 at_datetime=dt)

        goods_move.execute(dt_execution=self.dt_test2)
        self.assert_quantity(3, location=self.stock)
        self.assert_quantity(0, location=other)
        self.assert_quantity(3,
                             additional_states=['past'],
                             location=self.stock,
                             at_datetime=self.dt_test1)
        self.assert_quantity(0,
                             additional_states=['future'],
                             location=other,
                             at_datetime=self.dt_test1)
        for dt in (self.dt_test3, DATE_TIME_INFINITY):
            self.assert_quantity(2,
                                 additional_states=['future'],
                                 location=self.stock,
                                 at_datetime=dt)
            self.assert_quantity(1,
                                 additional_states=['future'],
                                 location=other,
                                 at_datetime=dt)

        loc_move.execute(dt_execution=self.dt_test3)
        for dt in (self.dt_test1, self.dt_test2):
            self.assert_quantity(3,
                                 additional_states=['past'],
                                 location=self.stock,
                                 at_datetime=dt)
            self.assert_quantity(0,
                                 additional_states=['past'],
                                 location=other,
                                 at_datetime=dt)
        for dt in (self.dt_test3, DATE_TIME_INFINITY):
            self.assert_quantity(2,
                                 additional_states=['past'],
                                 location=self.stock,
                                 at_datetime=dt)
            self.assert_quantity(1,
                                 additional_states=['past'],
                                 location=other,
                                 at_datetime=dt)
