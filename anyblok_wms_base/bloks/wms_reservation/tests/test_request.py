# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import ConcurrencyBlokTestCase


class RequestTestCase(ConcurrencyBlokTestCase):

    @classmethod
    def setUpCommonData(cls):
        cls.Reservation = cls.registry.Wms.Reservation
        inserted = cls.Reservation.Request.insert(purpose='why not?',
                                                  reserved=True)
        cls.request_id = inserted.id

    @classmethod
    def removeCommonData(cls):
        cls.Reservation.Request.query().get(cls.request_id).delete()

    def test_claim_no_concurrency(self):
        Request = self.Reservation.Request
        request = Request.query().get(self.request_id)
        owned = Request.txn_owned_reservations
        with Request.claim_reservations() as req_id:
            self.assertEqual(req_id, request.id)
            self.assertEqual(owned, set((req_id, )))
            self.assertTrue(request.is_txn_reservations_owner())

        # cleanup on exit of context manager does its job
        self.assertEqual(len(owned), 0)

        with Request.claim_reservations() as req_id:
            self.assertEqual(req_id, request.id)

    def test_claim_concurrency(self):
        Request = self.Reservation.Request
        Request2 = self.registry2.Wms.Reservation.Request
        # make sure that second transaction can see the request
        self.assertEqual(
            Request2.query().filter(Request2.id == self.request_id).count(), 1)
        with Request.claim_reservations() as req_id:
            claim_from_2 = Request2.claim_reservations
            with claim_from_2() as other_txn_claimed:
                self.assertIsNone(other_txn_claimed)
            with claim_from_2(request_id=req_id) as other_txn_claimed:
                self.assertIsNone(other_txn_claimed)
