# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta
from sqlalchemy import func
from anyblok_wms_base.testing import WmsTestCaseWithPhysObj
from anyblok_wms_base.exceptions import (
    OperationError,
    OperationInputsError,
    )


class TestAlterPlanning(WmsTestCaseWithPhysObj):
    """High level tests for alteration of chains of planned Operations."""

    def setUp(self):
        super(TestAlterPlanning, self).setUp()
        self.Move = self.Operation.Move

    def test_alter_dt_execution_too_early(self):
        stock = self.stock
        move = self.Move.create(destination=stock,
                                dt_execution=self.dt_test2,
                                state='planned',
                                input=self.avatar)
        # TODO more precise exc and testing of attributes
        with self.assertRaises(OperationError) as arc:
            move.alter_dt_execution(self.dt_test1 - timedelta(1))
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.operation, move)

    def test_alter_destination(self):
        outgoing = self.insert_location('OUTGOING')
        stock = self.stock
        move = self.Move.create(destination=stock,
                                dt_execution=self.dt_test2,
                                state='planned',
                                input=self.avatar)
        dep_input = move.outcome
        dep = self.Operation.Departure.create(
            dt_execution=self.dt_test3,
            state='planned',
            input=dep_input)
        record_callbacks = []

        def input_location_altered():
            record_callbacks.append(dep)

        dep.input_location_altered = input_location_altered
        move.alter_destination(outgoing)
        # the outcome of the Move is still the input of the Departure
        self.assert_singleton(move.outcomes, value=dep_input)
        self.assertEqual(dep_input.location, outgoing)

        # the hook has been called
        self.assert_singleton(record_callbacks, value=dep)

    def test_alter_dt_execution_before_departure(self):
        stock = self.stock
        move = self.Move.create(destination=stock,
                                dt_execution=self.dt_test2,
                                state='planned',
                                input=self.avatar)
        dep_input = move.outcome
        dep = self.Operation.Departure.create(
            dt_execution=self.dt_test3,
            state='planned',
            input=dep_input)

        new_dt = self.dt_test3 + timedelta(hours=1)

        move.alter_dt_execution(new_dt)

        self.assertEqual(move.dt_execution, new_dt)
        move_input = move.input
        self.assertEqual(move_input.dt_until, new_dt)
        self.assertEqual(move_input.dt_from, self.dt_test1)

        self.assertEqual(dep_input.dt_from, new_dt)
        self.assertEqual(dep_input.dt_until, new_dt)
        self.assertEqual(dep.dt_execution, new_dt)

    def test_alter_destination_before_unpack(self):
        incoming = self.incoming_loc
        stock = self.stock
        arrival = self.arrival
        unp_input = arrival.outcome

        # checking hypothesises
        self.assertEqual(arrival.location, incoming)
        self.assertEqual(unp_input.location, incoming)
        contents_type = self.PhysObj.Type.insert(label="Unpack outcomes",
                                                 code="UNP-OUTS")

        self.physobj_type.behaviours = dict(unpack=dict(outcomes=[
            dict(type=contents_type.code, quantity=3)]))

        unp = self.Operation.Unpack.create(input=unp_input,
                                           dt_execution=self.dt_test3,
                                           state='planned')
        unp_outcomes = unp.outcomes
        self.assertEqual(len(unp_outcomes), 3)
        first_unp_outcome = next(iter(unp_outcomes))
        # let's have at least one follower
        self.Operation.Departure.create(input=first_unp_outcome)

        # unpack is in-place:
        self.assertEqual(first_unp_outcome.location, incoming)

        # let's do it
        arrival.alter_destination(stock)
        self.assertEqual(arrival.location, stock)

        # the outcome of the Arrival is still the input of the Unpack
        self.assert_singleton(arrival.outcomes, value=unp_input)
        # but its location has been changed
        self.assertEqual(unp_input.location, stock)
        # and that's been propagated to the unpack outcomes
        self.assertTrue(all(oc.location == incoming) for oc in unp.outcomes)
        # which haven't changed btw
        self.MAXDIFF = None
        self.assertEqual(unp.outcomes, unp_outcomes)

    def test_inconsistent_alter_destination_before_assembly(self):
        incoming = self.incoming_loc
        stock = self.stock
        arrival1 = self.arrival
        arrival2 = self.Operation.Arrival.create(
            location=incoming,
            dt_execution=self.dt_test1,
            physobj_type=self.physobj_type)

        ass_inputs = [arrival1.outcome, arrival2.outcome]

        # checking hypothesises
        self.assertEqual(arrival1.location, incoming)
        assembled_type = self.PhysObj.Type.insert(
            code="ASSEMBLED",
            behaviours=dict(assembly=dict(default=dict(inputs=[
                dict(type=self.physobj_type.code, quantity=2)]))))
        ass = self.Operation.Assembly.create(inputs=ass_inputs,
                                             name='default',
                                             outcome_type=assembled_type)
        # By default Assembly happens in-place
        # (but Assembly can be overridden to not be in place)
        ass_out = self.assert_singleton(ass.outcomes)
        self.assertEqual(ass_out.location, incoming)

        self.Operation.Departure.create(input=ass_out,
                                        dt_execution=self.dt_test3)

        # changing only one of the Arrivals creates an inconsistency
        # in the assembly
        with self.assertRaises(OperationInputsError) as arc:
            arrival1.alter_destination(stock)

        exc = arc.exception
        self.assertEqual(set(exc.kwargs['locations']), {stock, incoming})

        # let's make it consistent again
        arrival2.alter_destination(stock)
        # outcome Avatar is the same one
        self.assert_singleton(ass.outcomes, value=ass_out)
        # but its location now has changed
        self.assertEqual(ass_out.location, stock)

    def test_refine_with_trailing_move_inapplicable(self):
        op = self.Operation.Observation.create(input=self.avatar)
        with self.assertRaises(OperationError) as arc:
            op.refine_with_trailing_move(self.stock)
        self.assertEqual(arc.exception.kwargs['op'], op)

    def test_refine_with_trailing_move(self):
        outgoing = self.insert_location('OUTGOING')
        stock = self.stock
        move = self.Move.create(destination=outgoing,
                                dt_execution=self.dt_test2,
                                state='planned',
                                input=self.avatar)
        dep_input = move.outcome
        dep = self.Operation.Departure.create(
            dt_execution=self.dt_test3,
            state='planned',
            input=dep_input)
        new_move = move.refine_with_trailing_move(stopover=stock)

        self.assertIsInstance(new_move, self.Move)
        self.assert_singleton(dep.follows, value=new_move)

        # follower's input hasn't changed (same instance)
        self.assert_singleton(dep.inputs, value=dep_input)

        # about the new intermediate Avatar
        new_av = self.assert_singleton(move.outcomes)
        self.assertNotEqual(new_av, dep_input)
        self.assertEqual(new_av.location, stock)
        self.assertEqual(new_av.obj, dep_input.obj)
        self.assertEqual(new_av.dt_from, self.avatar.dt_until)
        self.assertEqual(new_av.dt_until, self.dt_test3)

        self.assertEqual(dep_input.outcome_of, new_move)
        self.assertEqual(new_move.input, new_av)

    def test_refine_with_leading_move(self):
        outgoing = self.insert_location('OUTGOING')
        stock = self.stock
        move = self.Move.create(destination=stock,
                                dt_execution=self.dt_test2,
                                state='planned',
                                input=self.avatar)
        orig_dep_input = self.assert_singleton(move.outcomes)
        dep = self.Operation.Departure.create(
            dt_execution=self.dt_test3,
            state='planned',
            input=orig_dep_input)

        new_move = dep.refine_with_leading_move(stopover=outgoing)

        self.assertIsInstance(new_move, self.Move)
        self.assert_singleton(dep.follows, value=new_move)

        # follower's input hasn't changed (same instance)
        self.assert_singleton(move.outcomes, value=orig_dep_input)

        # about the new intermediate Avatar
        new_av = self.assert_singleton(new_move.outcomes)
        self.assertNotEqual(new_av, orig_dep_input)
        self.assertEqual(new_av.location, outgoing)
        self.assertEqual(new_av.obj, self.physobj)
        self.assertEqual(new_av.dt_from, self.dt_test3)
        self.assertEqual(new_av.dt_until, self.dt_test3)

        self.assertEqual(dep.input, new_av)
        self.assertEqual(new_move.destination, outgoing)
        self.assertEqual(new_move.input, orig_dep_input)

    def check_refine_arrivals_with_trailing_unpack(self,
                                                   dt_pack_arrival=None,
                                                   dt_unpack=None):
        Arrival = self.Operation.Arrival
        arrival, avatar = self.arrival, self.avatar
        arrival2 = Arrival.create(physobj_type=self.physobj_type,
                                  location=self.incoming_loc,
                                  state='planned',
                                  dt_execution=self.dt_test1)
        avatar2 = arrival2.outcome

        # downstream Operations, to validate that they won't be affected
        move = self.Operation.Move.create(input=avatar,
                                          destination=self.stock,
                                          dt_execution=self.dt_test3,
                                          state='planned')
        dep = self.Operation.Departure.create(input=avatar2,
                                              dt_execution=self.dt_test3,
                                              state='planned')

        pack_type = self.PhysObj.Type.insert(
            code='PACK',
            behaviours=dict(unpack=dict(
                uniform_outcomes=True,
                outcomes=[
                    dict(type=self.physobj_type.code,
                         quantity=3),
                    ]
                )))

        unpack = Arrival.refine_with_trailing_unpack(
            (arrival, arrival2),
            pack_type,
            dt_pack_arrival=dt_pack_arrival,
            dt_unpack=dt_unpack,
            pack_properties=dict(
                batch_ref='1337XO'),
            pack_code='PCK123')

        self.assertEqual(move.follows, dep.follows)
        self.assert_singleton(move.follows, value=unpack)
        self.assertEqual(len(unpack.outcomes), 3)
        # downstream Operation inputs are unchanged
        self.assertEqual(move.input, avatar)
        self.assertEqual(dep.input, avatar2)
        # but now they have a new property
        for av in (avatar, avatar2):
            self.assertEqual(av.obj.get_property('batch_ref'), '1337XO')

        # the two previous arrivals have been deleted, what remains is
        # the one of the pack
        new_arrival = self.assert_singleton(
            self.Operation.Arrival.query().all())
        self.assert_singleton(unpack.follows, value=new_arrival)

        # more about the pack
        self.assertEqual(unpack.input.obj.type, pack_type)
        return unpack

    def test_refine_arrivals_with_trailing_unpack_default_dt_arrival(self):
        unpack = self.check_refine_arrivals_with_trailing_unpack(
            dt_pack_arrival=None,
            dt_unpack=self.dt_test2)
        self.assertEqual(unpack.dt_execution, self.dt_test2)

    def test_refine_arrivals_with_trailing_unpack_default_dt_unpack(self):
        unpack = self.check_refine_arrivals_with_trailing_unpack(
            dt_pack_arrival=self.dt_test2,
            dt_unpack=None)
        self.assertEqual(unpack.dt_execution, self.dt_test2)

    def test_refine_arrivals_with_trailing_unpack_errors(self):
        Arrival = self.Operation.Arrival
        arrival = self.arrival

        # this is only about errors in the main method
        # the Unpack internal methods obviously would lead to more of them
        # with the parameters given below

        # no arrivals !
        with self.assertRaises(OperationError) as arc:
            Arrival.refine_with_trailing_unpack((), None)
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['arrivals'], ())

        # different locations
        arrival2 = Arrival.create(physobj_type=self.physobj_type,
                                  location=self.stock,
                                  state='planned',
                                  dt_execution=self.dt_test1)
        with self.assertRaises(OperationError) as arc:
            Arrival.refine_with_trailing_unpack((arrival, arrival2), None)
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['arrivals'], (arrival, arrival2))
        self.assertEqual(exc.kwargs['nb_locs'], 2)

    def test_use_case_improvements_operation_superseding(self):
        """Use case of improvements_superseding doc section"""
        Arrival = self.Operation.Arrival
        Move = self.Operation.Move
        unpack_area = self.insert_location('UNPACKING')
        incoming = self.incoming_loc

        unpacked_type = self.physobj_type
        stock = self.stock
        parcel_type = self.PhysObj.Type.insert(
            code='PARCEL',
            behaviours=dict(unpack=dict(
                # parcels's outcomes will be entirely specified dynamically
                # with the 'contents' property
                )))

        arrivals = []
        downstreams = []
        original_avatars = set()
        for i in range(5):
            arrival = Arrival.create(physobj_type=unpacked_type,
                                     location=unpack_area,
                                     state='planned',
                                     dt_execution=self.dt_test2)
            arrivals.append(arrival)
            arrived_av = self.assert_singleton(arrival.outcomes)
            original_avatars.add(arrived_av)
            downstream_kw = dict(input=arrived_av,
                                 state='planned',
                                 dt_execution=self.dt_test3)
            if i % 2:
                downstream = Move.create(destination=stock, **downstream_kw)
            else:
                downstream = self.Operation.Departure.create(**downstream_kw)
            downstreams.append(downstream)

        # say we get parcels with three units in each
        parcel_contents = [dict(type=unpacked_type.code, quantity=3)]

        unpacks = (
            Arrival.refine_with_trailing_unpack(
                arrivals[:3], parcel_type,
                dt_unpack=self.dt_test2,
                pack_properties=dict(contents=parcel_contents)),
            Arrival.refine_with_trailing_unpack(
                arrivals[3:], parcel_type,
                dt_unpack=self.dt_test2,
                pack_properties=dict(contents=parcel_contents))
        )
        # now we can be more precise about the parcels arrivals:
        # they will actually occur in the incoming location
        for unpack in unpacks:
            unpack_arrival = self.assert_singleton(unpack.follows)
            unpack_arrival.refine_with_trailing_move(stopover=incoming)

        # here's the final picture
        parcel_arrivals = Arrival.query().filter_by(
            physobj_type=parcel_type).all()
        self.assertEqual(len(parcel_arrivals), 2)
        all_unpacks_outcomes = set()
        for arr in parcel_arrivals:
            move = self.assert_singleton(arr.followers)
            self.assertIsInstance(move, Move)
            self.assertEqual(move.destination, unpack_area)
            unpack = self.assert_singleton(move.followers)
            self.assertEqual(len(unpack.outcomes), 3)
            all_unpacks_outcomes.update(unpack.outcomes)
        self.assertEqual(len(all_unpacks_outcomes), 6)
        self.assertTrue(original_avatars.issubset(all_unpacks_outcomes))

        # Downstream operations are attached to the unpacks outcomes,
        # and are still two downstream Moves and three Departures
        HI = self.Operation.HistoryInput
        Operation = self.Operation
        query = Operation.query(
            Operation.type, func.count(Operation.id))
        query = query.join(HI, HI.operation_id == Operation.id)
        query = query.group_by(Operation.type)
        downstream_op_types = {
            op_type: c for op_type, c in (
                Operation.query(Operation.type, func.count(Operation.id))
                .join(HI, Operation.id == HI.operation_id)
                .filter(HI.avatar_id.in_(
                    out.id for out in all_unpacks_outcomes))
                .group_by(Operation.type)
                .all())
        }
        self.assertEqual(downstream_op_types,
                         dict(wms_move=2, wms_departure=3))

        # the sixth unpacked item is dangling in the unpacking area
        dangling_av = self.assert_singleton(
            all_unpacks_outcomes.difference(original_avatars))
        self.assertEqual(dangling_av.location, unpack_area)


del WmsTestCaseWithPhysObj
