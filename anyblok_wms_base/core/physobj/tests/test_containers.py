# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.constants import DATE_TIME_INFINITY
from anyblok_wms_base.testing import WmsTestCase


class TestContainers(WmsTestCase):

    blok_entry_points = ('bloks', 'test_bloks')

    def setUp(self):
        super(TestContainers, self).setUp()
        self.Avatar = self.PhysObj.Avatar
        self.physobj_type = self.PhysObj.Type.insert(label="My goods",
                                                     code='MyGT')

        self.stock = self.insert_location('STK')

        # just a placeholder for subsequent Avatar insertions
        self.arrival = self.Operation.Arrival.insert(
            physobj_type=self.physobj_type,
            location=self.stock,
            dt_execution=self.dt_test1,
            state='done')

        self.default_quantity_location = self.stock

    def insert_goods(self, qty, state, dt_from, until=None, location=None):
        for _ in range(qty):
            self.Avatar.insert(
                obj=self.PhysObj.insert(type=self.physobj_type),
                outcome_of=self.arrival,
                location=self.stock if location is None else location,
                dt_from=dt_from,
                dt_until=until,
                state=state)

    def test_recursion(self):
        """Test flatten_containers_subquery recursion, demonstrating joins.
        """
        PhysObj = self.PhysObj
        sell_loc_type = self.location_type
        nosell_loc_type = self.Wms.PhysObj.Type.insert(
            code='NOSELL',
            behaviours=dict(container={}))
        stock_q = self.insert_location('STK/Q', parent=self.stock,
                                       location_type=nosell_loc_type)
        stock_2 = self.insert_location('STK/2', parent=self.stock)

        stock_q1 = self.insert_location('STK/Q1', parent=stock_q,
                                        location_type=nosell_loc_type)
        stock_qok = self.insert_location('STK/QOK', parent=stock_q)

        cte = PhysObj.flatten_containers_subquery(top=self.stock)
        self.assertEqual(
            set(r[0] for r in self.registry.session.query(cte.c.id).all()),
            {self.stock.id, stock_q.id, stock_2.id, stock_q1.id, stock_qok.id}
        )

        # example with no 'top', also demonstrating how to join (in this
        # case against on Location, to get full instances
        other = self.insert_location(
            'foo',
            location_type=self.Wms.PhysObj.Type.insert(
                code='NOSELL-OTHER',
                behaviours=dict(container={}))
        )
        cte = PhysObj.flatten_containers_subquery()
        joined = PhysObj.query().join(cte, cte.c.id == PhysObj.id)

        notsellable = set(joined.filter(PhysObj.type != sell_loc_type).all())
        self.assertEqual(notsellable, {stock_q, stock_q1, other})

        # Note that in this form, i.e. without joining on Avatars pointing to
        # the containers, there is nothing that actually restricts the
        # subquery to actually containers.
        self.insert_goods(1, 'present', self.dt_test1)
        self.assertIsNotNone(joined.filter(
            PhysObj.type == self.physobj_type).first())

    def test_flatten_subquery_moved(self):
        """Test the flatten subquery with planned Move of containers."""
        PhysObj = self.PhysObj
        stock = self.stock
        loc = self.insert_location('sub', parent=stock)
        loc_av = self.Avatar.query().filter_by(obj=loc).one()
        other = self.insert_location('other')
        loc_move = self.Operation.Move.create(input=loc_av,
                                              destination=other,
                                              state='planned',
                                              dt_execution=self.dt_test2)

        def assert_results(expected, **kwargs):
            cte = PhysObj.flatten_containers_subquery(**kwargs)
            self.assertEqual(
                set(PhysObj.query().join(cte, cte.c.id == PhysObj.id).all()),
                expected)

        # starting point, just to check
        assert_results({stock, loc}, top=stock)
        assert_results({other}, top=other)

        for dt in (self.dt_test2, self.dt_test3, DATE_TIME_INFINITY):
            assert_results({stock},
                           top=stock,
                           additional_states=['future'],
                           at_datetime=dt)
            assert_results({other, loc},
                           top=other,
                           additional_states=['future'],
                           at_datetime=dt)

        loc_move.execute(dt_execution=self.dt_test2)
        assert_results({stock}, top=stock)
        assert_results({other, loc}, top=other)

        assert_results({stock, loc},
                       top=stock,
                       additional_states=['past'],
                       at_datetime=self.dt_test1)

        assert_results({other},
                       top=other,
                       additional_states=['past'],
                       at_datetime=self.dt_test1)
