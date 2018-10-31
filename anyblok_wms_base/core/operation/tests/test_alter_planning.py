# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCaseWithPhysObj
from anyblok_wms_base.exceptions import (
    OperationInputsError,
    )


class TestAlterPlanning(WmsTestCaseWithPhysObj):
    """High level tests for alteration of chains of planned Operations."""

    def setUp(self):
        super(TestAlterPlanning, self).setUp()
        self.Move = self.Operation.Move

    def test_alter_destination(self):
        outgoing = self.insert_location('OUTGOING')
        stock = self.stock
        move = self.Move.create(destination=stock,
                                dt_execution=self.dt_test2,
                                state='planned',
                                input=self.avatar)
        dep_input = move.outcomes[0]
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

    def test_alter_destination_before_unpack(self):
        incoming = self.incoming_loc
        stock = self.stock
        arrival = self.arrival
        unp_input = arrival.outcomes[0]

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
        # let's have at least one follower
        self.Operation.Departure.create(input=unp_outcomes[0])

        # unpack is in-place:
        self.assertEqual(unp_outcomes[0].location, incoming)

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
        self.assertEqual(unp.outcomes, unp_outcomes)

    def test_inconsistent_alter_destination_before_assembly(self):
        incoming = self.incoming_loc
        stock = self.stock
        arrival1 = self.arrival
        arrival2 = self.Operation.Arrival.create(
            location=incoming,
            dt_execution=self.dt_test1,
            goods_type=self.physobj_type)

        ass_inputs = [arrival1.outcomes[0], arrival2.outcomes[0]]

        # checking hypothesises
        self.assertEqual(arrival1.location, incoming)
        assembled_type = self.PhysObj.Type.insert(
            code="ASSEMBLED",
            behaviours=dict(assembly=dict(default=dict(inputs=[
                dict(type=self.physobj_type.code, quantity=2)]))))
        ass = self.Operation.Assembly.create(inputs=ass_inputs,
                                             name='default',
                                             outcome_type=assembled_type)
        # Assembly happens in-place
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


del WmsTestCaseWithPhysObj
