# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCase
from anyblok_wms_base.exceptions import OperationGoodsReserved


class ReservationTestCase(WmsTestCase):

    def setUp(self):
        super(ReservationTestCase, self).setUp()
        Wms = self.registry.Wms
        self.Operation = Wms.Operation
        self.Reservation = Wms.Reservation

        self.goods_type = Wms.Goods.Type.insert(label="My good type",
                                                code="MyGT")
        self.incoming_loc = Wms.Location.insert(label="Incoming location")
        self.stock = Wms.Location.insert(label="Stock")

        arrival = self.Operation.Arrival.create(goods_type=self.goods_type,
                                                location=self.incoming_loc,
                                                state='planned',
                                                dt_execution=self.dt_test1)
        self.avatar = arrival.outcomes[0]
        self.goods = self.avatar.goods

    def test_authorized(self):
        request = self.Reservation.Request.insert(reserved=True)
        req_item = self.Reservation.RequestItem.insert(
            request=request,
            goods_type=self.goods_type,
            quantity=3)
        resa = self.Reservation.insert(goods=self.goods, request_item=req_item)

        # now it's reserved, and this txn hasn't authority, despite
        # being creator.
        with self.assertRaises(OperationGoodsReserved) as arc:
            self.Operation.Departure.create(input=self.avatar,
                                            dt_execution=self.dt_test2)
        exc_kw = arc.exception.kwargs
        self.assertEqual(exc_kw.get('goods'), self.goods)
        self.assertEqual(exc_kw.get('reservation'), resa)

        # all right, now let's gain some authority
        with request.claim_reservations(id=request.id):
            self.assertTrue(resa.is_transaction_owner())
            dep = self.Operation.Departure.create(input=self.avatar,
                                                  dt_execution=self.dt_test2)

        # reminder, at the end of the context manager, the current txn
        # does not own the reservation request any more:
        self.assertFalse(resa.is_transaction_owner())

        # but of course, anybody can execute the plan
        self.avatar.state = 'present'
        dep.execute()
