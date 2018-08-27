# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta

from .testcase import WmsTestCase
from anyblok_wms_base.exceptions import (
    OperationError,
    OperationInputsError,
    OperationIrreversibleError,
    )


class TestOperation(WmsTestCase):

    def setUp(self):
        super(TestOperation, self).setUp()
        Wms = self.registry.Wms
        self.Operation = Wms.Operation
        self.Goods = Wms.Goods
        self.incoming_loc = Wms.Location.insert(label="Incoming location")
        self.stock = Wms.Location.insert(label="Stock")
        self.goods_type = self.Goods.Type.insert(label="My good type",
                                                 code='MyGT')

    def test_execute_idempotency(self):
        op = self.Operation.Arrival.create(location=self.incoming_loc,
                                           state='planned',
                                           dt_execution=self.dt_test2,
                                           goods_type=self.goods_type)
        op.state = 'done'
        op.execute_planned = lambda: self.fail("Should not be called")
        op.execute()

    def test_history(self):
        arrival = self.Operation.Arrival.create(goods_type=self.goods_type,
                                                dt_execution=self.dt_test1,
                                                location=self.incoming_loc,
                                                state='planned')
        avatar = self.assert_singleton(arrival.outcomes)
        move = self.Operation.Move.create(destination=self.stock,
                                          dt_execution=self.dt_test2,
                                          state='planned',
                                          input=avatar)
        self.assertEqual(move.follows, [arrival])
        self.assertEqual(arrival.followers, [move])

    def test_len_inputs(self):
        arrival = self.Operation.Arrival.insert(goods_type=self.goods_type,
                                                dt_execution=self.dt_test1,
                                                location=self.incoming_loc,
                                                state='planned')
        Avatar = self.Goods.Avatar
        goods = [Avatar.insert(goods=self.Goods.insert(type=self.goods_type),
                               location=self.incoming_loc,
                               dt_from=self.dt_test1,
                               state='future',
                               reason=arrival)
                 for _ in (1, 2)]

        with self.assertRaises(OperationInputsError) as arc:
            self.Operation.Departure.create(inputs=goods,
                                            state='planned',
                                            dt_execution=self.dt_test2)
        self.assertEqual(arc.exception.kwargs.get('nb'), 2)

    def test_link_inputs(self):
        arrival = self.Operation.Arrival.insert(goods_type=self.goods_type,
                                                dt_execution=self.dt_test1,
                                                location=self.incoming_loc,
                                                state='planned')
        Avatar = self.Goods.Avatar
        avatars = [Avatar.insert(goods=self.Goods.insert(type=self.goods_type),
                                 location=self.incoming_loc,
                                 dt_from=self.dt_test1,
                                 dt_until=dt,
                                 state='future',
                                 reason=arrival)
                   for dt in (self.dt_test1, self.dt_test2, self.dt_test3)]

        HI = self.Operation.HistoryInput

        op = self.Operation.insert(state='done',
                                   dt_execution=self.dt_test3,
                                   type='wms_move')
        op.link_inputs(inputs=avatars[:1])
        self.assertEqual(op.inputs, avatars[:1])
        hi = self.single_result(HI.query().filter(HI.operation == op))
        self.assertEqual(hi.orig_dt_until, self.dt_test1)
        self.assertEqual(hi.latest_previous_op, arrival)

        op.link_inputs(inputs=avatars[1:2])
        self.assertEqual(op.inputs, avatars[:2])
        his = HI.query().filter(HI.operation == op).order_by(
            HI.orig_dt_until).all()
        self.assertEqual(len(his), 2)
        self.assertEqual(his[0], hi)
        self.assertEqual(his[1].orig_dt_until, self.dt_test2)
        self.assertEqual(his[1].latest_previous_op, arrival)

        op.link_inputs(inputs=avatars[2:], clear=True)
        self.assertEqual(op.inputs, avatars[2:])
        hi = self.single_result(HI.query().filter(HI.operation == op))
        self.assertEqual(hi.orig_dt_until, self.dt_test3)
        self.assertEqual(hi.latest_previous_op, arrival)

    def test_before_insert(self):
        other_loc = self.registry.Wms.Location.insert(code='other')

        def before_insert(inputs=None, **fields):
            """We're using it in this test to update the location.

            Arrival should indeed in check_create_conditions already
            test that it has a valid Location (but it doesn't at the time of
            this writing)
            """
            return inputs, dict(location=other_loc)

        Arrival = self.Operation.Arrival
        orig_before_insert = Arrival.before_insert
        Arrival.before_insert = before_insert
        try:
            arrival = Arrival.create(goods_type=self.goods_type,
                                     location=self.incoming_loc,
                                     dt_execution=self.dt_test1,
                                     state='planned')
        finally:
            Arrival.before_insert = orig_before_insert
        self.assertEqual(arrival.location, other_loc)
        # and it's been done at the right time, before creating outcomes
        self.assertEqual(arrival.outcomes[0].location, other_loc)

    def test_cancel(self):
        arrival = self.Operation.Arrival.create(goods_type=self.goods_type,
                                                location=self.incoming_loc,
                                                dt_execution=self.dt_test1,
                                                state='planned')
        Avatar = self.Goods.Avatar
        future_query = Avatar.query().filter(Avatar.state == 'future')
        self.assertEqual(future_query.count(), 1)

        arrival.cancel()
        self.assertEqual(future_query.count(), 0)
        self.assertEqual(self.Operation.Arrival.query().count(), 0)

    def test_cancel_done(self):
        """One can't cancel an operation that's already done."""
        arrival = self.Operation.Arrival.create(goods_type=self.goods_type,
                                                location=self.incoming_loc,
                                                dt_execution=self.dt_test1,
                                                state='done')
        with self.assertRaises(OperationError):
            arrival.cancel()

    def test_cancel_recursion(self):
        arrival = self.Operation.Arrival.create(goods_type=self.goods_type,
                                                location=self.incoming_loc,
                                                dt_execution=self.dt_test1,
                                                state='planned')
        goods = self.assert_singleton(arrival.outcomes)
        Move = self.Operation.Move
        Move.create(input=goods,
                    dt_execution=self.dt_test2,
                    destination=self.stock,
                    state='planned')
        move2 = Move.create(input=goods,
                            dt_execution=self.dt_test2,
                            destination=self.stock,
                            state='planned')
        self.registry.flush()
        avatar2 = self.assert_singleton(move2.outcomes)
        self.Operation.Departure.create(input=avatar2,
                                        dt_execution=self.dt_test3,
                                        state='planned')
        self.registry.flush()
        arrival.cancel()
        Avatar = self.Goods.Avatar
        self.assertEqual(Avatar.query().filter(
            Avatar.state == 'future').count(), 0)
        self.assertEqual(self.Operation.query().count(), 0)

    def test_plan_revert_recurse_linear(self):
        workshop = self.registry.Wms.Location.insert(label="Workshop")
        arrival = self.Operation.Arrival.create(goods_type=self.goods_type,
                                                location=self.incoming_loc,
                                                dt_execution=self.dt_test1,
                                                state='done')

        goods = self.assert_singleton(arrival.outcomes)  # an Avatar, really
        Move = self.Operation.Move

        # full moves don't generate splits, that's why the history is linear
        # (Splits are in wms-quantity only, now, anyway)
        move1 = Move.create(input=goods,
                            dt_execution=self.dt_test2,
                            destination=self.stock,
                            state='done')
        move2 = Move.create(input=self.assert_singleton(move1.outcomes),
                            dt_execution=self.dt_test3,
                            destination=workshop,
                            state='done')
        move1_rev, rev_leafs = move1.plan_revert(
            dt_execution=self.dt_test3 + timedelta(seconds=10))
        self.assertEqual(len(rev_leafs), 1)
        move2_rev = rev_leafs[0]

        self.assertEqual(move2_rev.state, 'planned')
        self.assertEqual(move2_rev.destination, self.stock)
        self.assertEqual(move2_rev.follows, [move2])
        self.assertEqual(move1_rev.state, 'planned')
        self.assertEqual(move1_rev.destination, self.incoming_loc)
        self.assertEqual(move1_rev.follows, [move2_rev])

        move2_rev.execute(self.dt_test3 + timedelta(1))
        rev_dt2 = self.dt_test3 + timedelta(2)
        move1_rev.execute(rev_dt2)

        Avatar = self.Goods.Avatar
        avatar = self.single_result(
            Avatar.query().filter(Avatar.state != 'past'))
        self.assertEqual(avatar.dt_from, rev_dt2)
        self.assertIsNone(avatar.dt_until)
        self.assertEqual(avatar.location, self.incoming_loc)

    def test_plan_revert_recurse_wrong_state(self):
        arrival = self.Operation.Arrival.create(goods_type=self.goods_type,
                                                location=self.incoming_loc,
                                                dt_execution=self.dt_test1,
                                                state='done')

        goods = self.assert_singleton(arrival.outcomes)
        move = self.Operation.Move.create(input=goods,
                                          dt_execution=self.dt_test2,
                                          destination=self.stock,
                                          state='planned')
        with self.assertRaises(OperationError):
            move.plan_revert()

    def test_plan_revert_recurse_irreversible(self):
        arrival = self.Operation.Arrival.create(goods_type=self.goods_type,
                                                location=self.incoming_loc,
                                                state='done',
                                                dt_execution=self.dt_test1)

        goods = self.assert_singleton(arrival.outcomes)  # an avatar, really

        move = self.Operation.Move.create(input=goods,
                                          destination=self.stock,
                                          dt_execution=self.dt_test2,
                                          state='done')

        outgoing = self.assert_singleton(move.outcomes)
        departure = self.Operation.Departure.create(input=outgoing,
                                                    dt_execution=self.dt_test3,
                                                    state='done')
        with self.assertRaises(OperationIrreversibleError) as arc:
            move.plan_revert()
        exc = arc.exception
        str(exc)
        self.assertEqual(exc.kwargs.get('op'), departure)

    def test_obliviate_planned(self):
        arrival = self.Operation.Arrival.create(goods_type=self.goods_type,
                                                location=self.incoming_loc,
                                                dt_execution=self.dt_test1,
                                                state='planned')
        # No need to go in detail, we'll probably want to fallback to cancel()
        # actually in that case
        with self.assertRaises(OperationError):
            arrival.obliviate()

    def test_obliviate_recurse_linear(self):
        workshop = self.registry.Wms.Location.insert(label="Workshop")
        arrival = self.Operation.Arrival.create(goods_type=self.goods_type,
                                                location=self.incoming_loc,
                                                dt_execution=self.dt_test1,
                                                state='done')

        goods = self.assert_singleton(arrival.outcomes)  # an avatar, really
        Move = self.Operation.Move

        # full moves don't generate splits, that's why the history is linear
        move1 = Move.create(input=goods,
                            dt_execution=self.dt_test2,
                            destination=self.stock,
                            state='done')
        Move.create(input=self.assert_singleton(move1.outcomes),
                    dt_execution=self.dt_test3,
                    destination=workshop,
                    state='done')
        move1.obliviate()

        Avatar = self.Goods.Avatar
        avatar = self.single_result(
            Avatar.query().filter(Avatar.state != 'past'))
        self.assertEqual(avatar.location, self.incoming_loc)
        self.assertEqual(avatar.dt_from, self.dt_test1)
        self.assertEqual(avatar.dt_until, None)

        self.assertEqual(Move.query().count(), 0)

    def test_planned_dt_execution_required(self):
        with self.assertRaises(OperationError) as arc:
            self.Operation.Arrival.create(goods_type=self.goods_type,
                                          location=self.incoming_loc,
                                          state='planned')
        exc = arc.exception
        self.assertEqual(exc.kwargs.get('state'), 'planned')
