# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from datetime import datetime
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
        PhysObj = self.PhysObj
        self.incoming_loc = self.insert_location('INCOMING')
        self.stock = self.insert_location('STOCK')

        self.physobj_type = PhysObj.Type.insert(label="My good type",
                                                code='MyGT')

    def test_execute_idempotency(self):
        op = self.Operation.Arrival.create(location=self.incoming_loc,
                                           state='planned',
                                           dt_execution=self.dt_test2,
                                           physobj_type=self.physobj_type)
        op.state = 'done'
        op.execute_planned = lambda: self.fail("Should not be called")
        op.execute()

    def test_history(self):
        arrival = self.Operation.Arrival.create(physobj_type=self.physobj_type,
                                                dt_execution=self.dt_test1,
                                                location=self.incoming_loc,
                                                state='planned')
        avatar = self.assert_singleton(arrival.outcomes)
        move = self.Operation.Move.create(destination=self.stock,
                                          dt_execution=self.dt_test2,
                                          state='planned',
                                          input=avatar)
        self.assert_singleton(move.follows, value=arrival)
        self.assert_singleton(arrival.followers, value=move)

    def test_len_inputs(self):
        arrival = self.Operation.Arrival.insert(physobj_type=self.physobj_type,
                                                dt_execution=self.dt_test1,
                                                location=self.incoming_loc,
                                                state='planned')
        Avatar = self.PhysObj.Avatar
        goods = [Avatar.insert(obj=self.PhysObj.insert(type=self.physobj_type),
                               location=self.incoming_loc,
                               dt_from=self.dt_test1,
                               state='future',
                               outcome_of=arrival)
                 for _ in (1, 2)]

        with self.assertRaises(OperationInputsError) as arc:
            self.Operation.Departure.create(inputs=goods,
                                            state='planned',
                                            dt_execution=self.dt_test2)
        self.assertEqual(arc.exception.kwargs.get('nb'), 2)

    def test_link_inputs(self):
        arrival = self.Operation.Arrival.insert(physobj_type=self.physobj_type,
                                                dt_execution=self.dt_test1,
                                                location=self.incoming_loc,
                                                state='planned')
        Avatar = self.PhysObj.Avatar
        avatars = [
            Avatar.insert(
                obj=self.PhysObj.insert(type=self.physobj_type),
                location=self.incoming_loc,
                dt_from=self.dt_test1,
                dt_until=dt,
                state='future',
                outcome_of=arrival)
            for dt in (self.dt_test1, self.dt_test2, self.dt_test3)]

        HI = self.Operation.HistoryInput

        # using a Move instead of a bare Wms.Operation, so that
        # SQLAlchemy doesn't complain about inconsistent polymorphism
        # (we would need to pass a correct type (``wms_move``),
        # but a bare Wms.Operation would not be of the appropriate class)
        op = self.Operation.Move.insert(state='done',
                                        destination=self.stock,
                                        dt_execution=self.dt_test3)
        op.link_inputs(inputs=avatars[:1])
        self.assertEqual(op.inputs, avatars[:1])
        hi = self.single_result(HI.query().filter(HI.operation == op))
        self.assert_singleton(op.follows, value=arrival)

        op.link_inputs(inputs=avatars[1:2])
        self.assertEqual(op.inputs, avatars[:2])
        his = set(HI.query().filter(HI.operation == op).all())
        self.assertEqual(len(his), 2)
        self.assertTrue(hi in his)
        self.assert_singleton(op.follows, value=arrival)

        op.link_inputs(inputs=avatars[2:], clear=True)
        self.assertEqual(op.inputs, avatars[2:])
        hi = self.single_result(HI.query().filter(HI.operation == op))
        self.assert_singleton(op.follows, value=arrival)

    def test_inputs_terminal(self):
        """In regular Operation creations, all inputs should be terminal."""

        arrival = self.Operation.Arrival.create(physobj_type=self.physobj_type,
                                                dt_execution=self.dt_test1,
                                                location=self.incoming_loc,
                                                state='planned')
        arrived = arrival.outcome
        self.Operation.Move.create(input=arrived,
                                   destination=self.stock,
                                   dt_execution=self.dt_test2)

        with self.assertRaises(OperationInputsError) as arc:
            self.Operation.Move.create(input=arrived,
                                       destination=self.stock,
                                       dt_execution=self.dt_test3)
        exc = arc.exception
        self.assertEqual(exc.kwargs.get('avatar'), arrived)

    def test_before_insert(self):
        other_loc = self.insert_location('other')

        def before_insert(inputs=None, **fields):
            """We're using it in this test to update the location.

            Arrival should indeed in check_create_conditions already
            test that it has a valid location (but it doesn't at the time of
            this writing)
            """
            return inputs, dict(location=other_loc)

        Arrival = self.Operation.Arrival
        orig_before_insert = Arrival.before_insert
        Arrival.before_insert = before_insert
        try:
            arrival = Arrival.create(physobj_type=self.physobj_type,
                                     location=self.incoming_loc,
                                     dt_execution=self.dt_test1,
                                     state='planned')
        finally:
            Arrival.before_insert = orig_before_insert
        self.assertEqual(arrival.location, other_loc)
        # and it's been done at the right time, before creating outcomes
        self.assertEqual(arrival.outcome.location, other_loc)

    def test_cancel(self):
        arrival = self.Operation.Arrival.create(physobj_type=self.physobj_type,
                                                location=self.incoming_loc,
                                                dt_execution=self.dt_test1,
                                                state='planned')
        Avatar = self.PhysObj.Avatar
        future_query = Avatar.query().filter(Avatar.state == 'future')
        self.assertEqual(future_query.count(), 1)

        arrival.cancel()
        self.assertEqual(future_query.count(), 0)
        self.assertEqual(self.Operation.Arrival.query().count(), 0)

    def test_cancel_done(self):
        """One can't cancel an operation that's already done."""
        arrival = self.Operation.Arrival.create(physobj_type=self.physobj_type,
                                                location=self.incoming_loc,
                                                dt_execution=self.dt_test1,
                                                state='done')
        with self.assertRaises(OperationError):
            arrival.cancel()

    def test_cancel_recursion(self):
        arrival = self.Operation.Arrival.create(physobj_type=self.physobj_type,
                                                location=self.incoming_loc,
                                                dt_execution=self.dt_test1,
                                                state='planned')
        avatar1 = self.assert_singleton(arrival.outcomes)
        Move = self.Operation.Move
        move1 = Move.create(input=avatar1,
                            dt_execution=self.dt_test2,
                            destination=self.stock,
                            state='planned')
        move2 = Move.create(input=move1.outcome,
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
        Avatar = self.PhysObj.Avatar
        self.assertEqual(Avatar.query()
                         .filter(Avatar.state == 'future')
                         .count(),
                         0)
        self.assertEqual(self.Operation.query().count(), 0)

    def test_plan_revert_recurse_linear(self):
        workshop = self.PhysObj.insert(code="Workshop",
                                       type=self.stock.type)
        arrival = self.Operation.Arrival.create(physobj_type=self.physobj_type,
                                                location=self.incoming_loc,
                                                dt_execution=self.dt_test1,
                                                state='done')

        Move = self.Operation.Move

        # full moves don't generate splits, that's why the history is linear
        # (Splits are in wms-quantity only, now, anyway)
        move1 = Move.create(input=arrival.outcome,
                            dt_execution=self.dt_test2,
                            destination=self.stock,
                            state='done')
        move2 = Move.create(input=move1.outcome,
                            dt_execution=self.dt_test3,
                            destination=workshop,
                            state='done')
        move1_rev, rev_leafs = move1.plan_revert(
            dt_execution=self.dt_test3 + timedelta(seconds=10))
        self.assertEqual(len(rev_leafs), 1)
        move2_rev = rev_leafs[0]

        self.assertEqual(move2_rev.state, 'planned')
        self.assertEqual(move2_rev.destination, self.stock)
        self.assert_singleton(move2_rev.follows, value=move2)
        self.assertEqual(move1_rev.state, 'planned')
        self.assertEqual(move1_rev.destination, self.incoming_loc)
        self.assert_singleton(move1_rev.follows, value=move2_rev)

        move2_rev.execute(self.dt_test3 + timedelta(1))

        rev_dt2 = self.dt_test3 + timedelta(2)
        move1_rev.execute(rev_dt2)

        Avatar = self.PhysObj.Avatar
        avatar = self.single_result(
            Avatar.query().filter(Avatar.state != 'past'))
        self.assertEqual(avatar.dt_from, rev_dt2)
        self.assertIsNone(avatar.dt_until)
        self.assertEqual(avatar.location, self.incoming_loc)

    def test_plan_revert_recurse_wrong_state(self):
        arrival = self.Operation.Arrival.create(physobj_type=self.physobj_type,
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
        arrival = self.Operation.Arrival.create(physobj_type=self.physobj_type,
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
        arrival = self.Operation.Arrival.create(physobj_type=self.physobj_type,
                                                location=self.incoming_loc,
                                                dt_execution=self.dt_test1,
                                                state='planned')
        # No need to go in detail, we'll probably want to fallback to cancel()
        # actually in that case
        with self.assertRaises(OperationError):
            arrival.obliviate()

    def test_obliviate_recurse_linear(self):
        workshop = self.PhysObj.insert(code="Workshop",
                                       type=self.stock.type)
        arrival = self.Operation.Arrival.create(physobj_type=self.physobj_type,
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

        Avatar = self.PhysObj.Avatar
        avatar = self.single_result(
            Avatar.query().filter(Avatar.state != 'past'))
        self.assertEqual(avatar.location, self.incoming_loc)
        self.assertEqual(avatar.dt_from, self.dt_test1)
        self.assertEqual(avatar.dt_until, None)

        self.assertEqual(Move.query().count(), 0)

    def test_planned_default_dt_execution_no_inputs(self):
        now = datetime.now(tz=self.dt_test1.tzinfo)
        arr = self.Operation.Arrival.create(physobj_type=self.physobj_type,
                                            location=self.incoming_loc,
                                            state='planned')
        self.assertTrue(arr.dt_execution > now)

    def test_planned_default_dt_execution_inputs(self):
        arr = self.Operation.Arrival.create(physobj_type=self.physobj_type,
                                            location=self.incoming_loc,
                                            dt_execution=self.dt_test1,
                                            state='planned')
        departure = self.Operation.Departure.create(input=arr.outcome)
        self.assertEqual(departure.dt_execution, self.dt_test1)

    def test_check_alterable(self):
        arr = self.Operation.Arrival.create(physobj_type=self.physobj_type,
                                            location=self.incoming_loc,
                                            dt_execution=self.dt_test1,
                                            state='planned')
        arr.check_alterable()
        arr.state = 'done'
        with self.assertRaises(OperationError) as arc:
            arr.check_alterable()
        exc = arc.exception
        str(exc)
        self.assertEqual(exc.kwargs.get('op'), arr)
        self.assertEqual(exc.kwargs.get('state'), 'done')

    def test_alter_with_trailing_move_inapplicable(self):
        arr = self.Operation.Arrival.create(physobj_type=self.physobj_type,
                                            location=self.incoming_loc,
                                            dt_execution=self.dt_test1,
                                            state='planned')
        avatar = self.assert_singleton(arr.outcomes)
        dep = self.Operation.Departure.create(input=avatar,
                                              dt_execution=self.dt_test2,
                                              state='planned')
        with self.assertRaises(OperationError) as arc:
            dep.alter_destination(self.stock)
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs.get('op'), dep)

    def test_transitive_followers(self):

        # we'll monkey-patch the Operation base class heavily to
        # focus on the algorithm.
        followers_orig_prop = self.Operation.followers
        self.Operation.followers = None  # allows to set attr on instances

        def op(oid, followers=()):
            # not inserted, none of the db constraints applies.
            o = self.Operation.Arrival(id=oid)
            o.followers = followers
            return o

        try:
            # test case inspired by
            # https://algorithms.tutorialhorizon.com/topological-sort/
            # the graph contains two nice diamond shapes included in each other.
            a0 = op(0)
            a1 = op(1, followers=[a0])
            a2 = op(2, followers=[a1])
            a3 = op(3, followers=[a1])
            a4 = op(4)
            a5 = op(5, followers=[a4, a2])
            a6 = op(6, followers=[a4, a3])
            a7 = op(7, followers=[a5, a6])

            # for now the algorithm is deterministic, because the followers
            # that we injected directly are lists and it iterates simply on it.
            res = a7.transitive_followers()
            self.assertEqual(res, [a6, a3, a5, a2, a1, a0, a4])
            # just to be sure...
            for a in res:
                for f in a.followers:
                    self.assertLess(res.index(a), res.index(f))

        finally:
            self.Operation.followers = followers_orig_prop
