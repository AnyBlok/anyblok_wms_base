# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import ConcurrencyBlokTestCase
from anyblok_wms_base.testing import WmsTestCase


class RequestItemTestCase(WmsTestCase):

    def setUp(self):
        super(RequestItemTestCase, self).setUp()
        Wms = self.registry.Wms
        self.PhysObj = Wms.PhysObj
        self.Props = self.PhysObj.Properties
        self.Reservation = Wms.Reservation
        self.RequestItem = self.Reservation.RequestItem
        self.loc = self.insert_location('INC')
        gt1 = self.goods_type1 = self.PhysObj.Type.insert(code='MG')
        gt2 = self.goods_type2 = self.PhysObj.Type.insert(code='MH')

        # just so that we can insert avatars
        self.arrival = Wms.Operation.Arrival.insert(
            physobj_type=gt1,
            state='planned',
            dt_execution=self.dt_test1,
            location=self.loc)

        p1 = self.props1 = self.Props.insert(flexible=dict(foo=3))
        p2 = self.props2 = self.Props.insert(flexible=dict(foo=7),
                                             batch='ABCD')

        self.goods = {
            p1: [self.PhysObj.insert(type=gt1, properties=p1),
                 self.PhysObj.insert(type=gt1, properties=p1),
                 self.PhysObj.insert(type=gt2, properties=p1),
                 ],
            p2: [self.PhysObj.insert(type=gt1, properties=p2),
                 self.PhysObj.insert(type=gt2, properties=p2),
                 ],
        }
        self.avatars = {g: self.PhysObj.Avatar.insert(obj=g,
                                                      dt_from=self.dt_test1,
                                                      location=self.loc,
                                                      outcome_of=self.arrival,
                                                      state='present')
                        for perprop in self.goods.values() for g in perprop}

    def test_lookup(self):
        item = self.RequestItem(goods_type=self.goods_type1,
                                properties=dict(foo=3),
                                quantity=20)
        self.assertEqual(set(item.lookup(2)),
                         set((1, g) for g in self.goods[self.props1][:2]))
        item = self.RequestItem(goods_type=self.goods_type1,
                                properties=dict(batch='ABCD'),
                                quantity=20)
        self.assertEqual(item.lookup(10), [(1, self.goods[self.props2][0])])

    def test_lookup_no_props(self):
        item = self.RequestItem(goods_type=self.goods_type1,
                                quantity=20)
        for found in item.lookup(2):
            self.assertEqual(found[1].type, self.goods_type1)

    def test_item_reserve(self):
        # requesting 3 PhysObj records, but only 2 will match
        item = self.RequestItem(goods_type=self.goods_type1,
                                properties=dict(foo=3),
                                quantity=3)
        self.assertFalse(item.reserve())  # it's not fully reserved yet

        resas = self.Reservation.query().all()
        for resa in resas:
            self.assertEqual(resa.quantity, 1)
        first_two = set(r.physobj for r in resas)
        self.assertEqual(first_two, set(self.goods[self.props1][:2]))

        av3, av4 = [
            self.PhysObj.Avatar.insert(
                state='future',
                obj=self.PhysObj.insert(type=self.goods_type1,
                                        properties=self.props1),
                outcome_of=self.arrival,
                dt_from=self.dt_test1,
                location=self.loc)
            for i in (3, 4)]

        self.assertEqual(item.reserve(), True)  # now it's satisfied

        # we needed only one more, so there's one PhysObj that's not reserved
        all_three = set(r.physobj for r in self.Reservation.query().all())
        self.assertEqual(len(all_three), 3)
        self.assertTrue(first_two.issubset(all_three))
        self.assertTrue(av3.obj in all_three or av4.obj in all_three)

        # subsequent executions don't reserve more
        self.assertEqual(item.reserve(), True)
        self.assertEqual(self.Reservation.query().count(), 3)

    def test_request_reserve(self):
        req = self.Reservation.Request(purpose="some delivery")
        self.RequestItem.insert(goods_type=self.goods_type1,
                                properties=dict(foo=3),
                                quantity=2,
                                request=req)
        self.RequestItem.insert(goods_type=self.goods_type2,
                                properties=dict(batch='ABCD'),
                                quantity=1,
                                request=req)
        self.assertTrue(req.reserve())
        self.assertTrue(req.reserved)
        reserved_goods = set(r.physobj for r in self.Reservation.query().all())
        expected = set((self.goods[self.props1][:2]))
        expected.add(self.goods[self.props2][1])
        self.assertEqual(reserved_goods, expected)

        # idempotency
        req.reserve()
        self.assertEqual(self.Reservation.query().count(), 3)

    def test_request_reserve_all(self):
        Request = self.Reservation.Request
        req1 = Request.insert(purpose=dict(nb=1))
        self.RequestItem.insert(goods_type=self.goods_type1,
                                properties=dict(foo=3),
                                quantity=2,
                                request=req1)
        req2 = Request.insert(purpose=dict(nb=2))
        self.RequestItem.insert(goods_type=self.goods_type2,
                                properties=dict(batch='ABCD'),
                                quantity=1,
                                request=req2)
        # and now an unsatisfiable one:
        req3 = Request.insert(purpose=dict(nb=3))
        self.RequestItem.insert(goods_type=self.goods_type2,
                                properties=dict(batch="don't exist"),
                                quantity=12,
                                request=req3)

        # TODO ask jssuzanne why in test case's registry, commit is disabled
        # but not in Request's registry (thought it was txn not being Root?)
        # TODO use mock.patch contextmanager (IIRC)
        saved_commit = Request.registry.commit
        Request.registry.commit = lambda: None
        try:
            Request.reserve_all(batch_size=1)
        finally:
            Request.registry.commit = saved_commit

        self.assertTrue(req1.reserved)
        self.assertTrue(req2.reserved)
        reserved_goods = set(r.physobj for r in self.Reservation.query().all())
        expected = set((self.goods[self.props1][:2]))
        expected.add(self.goods[self.props2][1])
        self.assertEqual(reserved_goods, expected)

    def test_reserve_avatars_once(self):
        """We don't reserve several times PhysObj that have several Avatars."""
        goods = self.goods[self.props1][0]
        for av in self.avatars.values():
            # can't have several 'present' Avatars for one physicial object
            av.update(state='future', obj=goods)
        self.registry.flush()  # to be sure

        item = self.RequestItem(goods_type=self.goods_type1,
                                properties=dict(foo=3),
                                quantity=12)
        item.reserve()
        resa = self.single_result(self.Reservation.query())
        self.assertEqual(resa.physobj, goods)

    def test_dont_reserve_past_avatars(self):
        """We don't reserve PhysObj that have only 'past' avatars."""
        for av in self.avatars.values():
            av.state = 'past'
        self.registry.flush()  # to be sure

        item = self.RequestItem(goods_type=self.goods_type1,
                                properties=dict(foo=3),
                                quantity=12)
        item.reserve()
        self.assertEqual(self.Reservation.query().count(), 0)

        goods = self.goods[self.props1][0]
        self.avatars[goods].state = 'future'
        item.reserve()

        resa = self.single_result(self.Reservation.query())
        self.assertEqual(resa.physobj, goods)


class RequestClaimTestCase(ConcurrencyBlokTestCase):

    @classmethod
    def setUpCommonData(cls):
        cls.Reservation = cls.registry.Wms.Reservation
        inserted = cls.Reservation.Request.insert(purpose=dict(why='not?'),
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

        with Request.claim_reservations(planned=False) as req_id:
            self.assertEqual(req_id, request.id)

        request.planned = True
        with Request.claim_reservations(planned=False) as req_id:
            self.assertIsNone(req_id)

        # now with a provided base query
        query = (Request.query(Request.id)
                 .filter(Request.purpose.contains(dict(why='not?'))))
        with Request.claim_reservations(query=query) as req_id:
            self.assertEqual(req_id, request.id)

        query = (Request.query(Request.id)
                 .filter(Request.purpose.contains(dict(why='because'))))
        with Request.claim_reservations(query=query) as req_id:
            self.assertIsNone(req_id)

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
            with claim_from_2(id=req_id) as other_txn_claimed:
                self.assertIsNone(other_txn_claimed)


class RequestLockUnreservedTestCase(ConcurrencyBlokTestCase):

    def setUp(self):
        super(ConcurrencyBlokTestCase, self).setUp()
        self.Request = self.registry.Wms.Reservation.Request
        self.Request2 = self.registry2.Wms.Reservation.Request

        # we'll get different instances in each test, backed
        # by the same database rows (no point storing them on the class)
        self.requests = set(self.Request.query().all())

    @classmethod
    def setUpCommonData(cls):
        cls.Reservation = cls.registry.Wms.Reservation
        for i in range(4):
            cls.Reservation.Request.insert(purpose=dict(bar=i),
                                           reserved=False)

    @classmethod
    def removeCommonData(cls):
        cls.Reservation.query().delete()
        cls.Reservation.RequestItem.query().delete()
        cls.Reservation.Request.query().delete()

    def test_lock_unreserved_concurrency(self):
        locked = self.Request.lock_unreserved(5)
        self.assertEqual(set(locked), self.requests)

        with self.assertRaises(self.Request.ReservationsLocked):
            self.Request2.reserve_all(retry_delay=0.01, nb_attempts=2)

    def test_lock_unreserved_avoid_concurrency(self):
        """Caller can filter requests to avoid concurrency."""

        def query_filter(Request, purpose_nb, query):
            return query.filter(Request.purpose.contains(dict(bar=purpose_nb)))

        locked = self.Request.lock_unreserved(
            5,
            query_filter=lambda q: query_filter(self.Request, 2, q))

        self.assertEqual(len(locked), 1)
        self.assertEqual(locked[0].purpose, dict(bar=2))

        # TODO ask jssuzanne why in test case's registry, commit is disabled
        # but not in Request's registry (thought it was txn not being Root?)
        # TODO use mock.patch contextmanager (IIRC)
        saved_commit = self.Request2.registry.commit
        self.Request2.registry.commit = lambda: None
        self.Request2.reserve_all(
            query_filter=lambda q: query_filter(self.Request2, 3, q))
        self.Request2.commit = saved_commit

        # the only selected Request is considered reserved: since it has
        # actually no item, all of them have been fulfilled
        req = (self.Request2.query()
               .filter(self.Request2.purpose.contains(dict(bar=3)))
               .one())
        self.assertTrue(req.reserved)

    def test_reserve_all(self):
        Request = self.Request
        # TODO ask jssuzanne why in test case's registry, commit is disabled
        # but not in Request's registry (thought it was txn not being Root?)
        # TODO use mock.patch contextmanager (IIRC)
        saved_commit = Request.registry.commit
        Request.registry.commit = lambda: None

        Request.reserve_all()

        Request.registry.commit = saved_commit
