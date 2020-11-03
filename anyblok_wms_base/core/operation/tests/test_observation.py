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
    ObservationError,
    )


class TestObservation(WmsTestCaseWithPhysObj):

    def setUp(self):
        super(TestObservation, self).setUp()
        self.Observation = self.Operation.Observation

    def test_planned_execute(self):
        obs = self.Observation.create(state='planned',
                                      dt_execution=self.dt_test2,
                                      input=self.avatar)

        self.assert_singleton(obs.follows, value=self.arrival)
        self.assertEqual(obs.input, self.avatar)
        self.assertEqual(self.avatar.dt_until, self.dt_test2)
        outcome = self.assert_singleton(obs.outcomes)

        self.assertEqual(outcome.dt_from, self.dt_test2)
        self.assertIsNone(outcome.dt_until)

        self.avatar.state = 'present'
        obs.observed_properties = dict(qa='ok')
        obs.execute(self.dt_test3)

        self.assertEqual(obs.state, 'done')
        self.assertEqual(self.physobj.get_property('qa'), 'ok')
        self.assertEqual(self.avatar.state, 'past')
        self.assertEqual(outcome.state, 'present')

    def test_planned_input_present(self):
        self.avatar.state = 'present'
        obs = self.Observation.create(state='planned',
                                      dt_execution=self.dt_test2,
                                      input=self.avatar)

        self.assertEqual(obs.outcome.state, 'future')
        self.assertEqual(obs.input.state, 'present')

    def test_done(self):
        self.avatar.state = 'present'
        obs = self.Observation.create(state='done',
                                      observed_properties=dict(qa='ok'),
                                      dt_execution=self.dt_test2,
                                      input=self.avatar)

        self.assert_singleton(obs.follows, value=self.arrival)
        self.assertEqual(obs.input, self.avatar)
        self.assertEqual(obs.state, 'done')

        self.assertEqual(self.physobj.get_property('qa'), 'ok')
        self.assertEqual(self.avatar.dt_until, self.dt_test2)
        self.assertEqual(self.avatar.state, 'past')

        outcome = self.assert_singleton(obs.outcomes)
        self.assertEqual(outcome.dt_from, self.dt_test2)
        self.assertIsNone(outcome.dt_until)
        self.assertEqual(outcome.state, 'present')

    def test_planned_required_execute(self):
        obs = self.Observation.create(state='planned',
                                      required_properties=['qa', 'grade'],
                                      dt_execution=self.dt_test2,
                                      input=self.avatar)

        self.assert_singleton(obs.follows, value=self.arrival)
        self.assertEqual(obs.input, self.avatar)
        self.assertEqual(self.avatar.dt_until, self.dt_test2)
        outcome = self.assert_singleton(obs.outcomes)

        self.assertEqual(outcome.dt_from, self.dt_test2)
        self.assertIsNone(outcome.dt_until)

        self.avatar.state = 'present'
        obs.observed_properties = dict(qa='ok')
        with self.assertRaises(ObservationError) as arc:
            obs.execute(self.dt_test3)
        exc = arc.exception
        self.assertEqual(set(exc.kwargs['required']), {'qa', 'grade'})
        self.assertEqual(set(exc.kwargs['observed']), {'qa'})

    def test_done_no_props_obliviate(self):
        """Oblivion in case there were no props at all to start with."""
        avatar = self.avatar
        phobj = avatar.obj
        avatar.state = 'present'

        # checking pre-assumptions
        self.assertFalse('qa' in phobj.merged_properties())
        obs = self.Observation.create(state='done',
                                      observed_properties=dict(qa='ok'),
                                      dt_execution=self.dt_test2,
                                      input=self.avatar)

        self.assertEqual(phobj.properties.get('qa'), 'ok')

        obs.obliviate()
        self.assertFalse('qa' in phobj.merged_properties())

    def test_done_new_prop_obliviate(self):
        """Oblivion in case the prop is new, but it's not the first one."""
        avatar = self.avatar
        phobj = avatar.obj
        avatar.state = 'present'

        phobj.set_property('serial', 12345)
        # checking pre-assumptions
        self.assertFalse('qa' in phobj.merged_properties())
        obs = self.Observation.create(state='done',
                                      observed_properties=dict(qa='ok'),
                                      dt_execution=self.dt_test2,
                                      input=self.avatar)

        self.assertEqual(phobj.properties.get('qa'), 'ok')

        obs.obliviate()
        self.assertFalse('qa' in phobj.merged_properties())

    def test_done_changed_prop_obliviate(self):
        self.avatar.state = 'present'
        phobj = self.avatar.obj

        phobj.set_property('qa', 'ok')
        obs = self.Observation.create(state='done',
                                      observed_properties=dict(qa='nok'),
                                      dt_execution=self.dt_test2,
                                      input=self.avatar)

        self.assertEqual(phobj.properties.get('qa'), 'nok')

        obs.obliviate()

        self.assertEqual(phobj.properties['qa'], 'ok')
        self.assertEqual(phobj.merged_properties()['qa'], 'ok')

    def test_done_overridden_obliviate(self):
        self.avatar.state = 'present'
        phobj = self.avatar.obj

        phobj.type.properties = dict(qa='ok')
        self.assertEqual(phobj.get_property('qa'), 'ok')
        obs = self.Observation.create(state='done',
                                      observed_properties=dict(qa='nok'),
                                      dt_execution=self.dt_test2,
                                      input=self.avatar)
        self.assertEqual(phobj.properties.get('qa'), 'nok')

        obs.obliviate()

        self.assertFalse('ok' in phobj.properties)
        self.assertEqual(phobj.merged_properties()['qa'], 'ok')

    def test_done_revert_middle_of_chain(self):
        Move = self.Operation.Move
        outgoing = self.insert_location('OUTGOING')
        self.avatar.state = 'present'
        phobj = self.avatar.obj

        pre_move = Move.create(input=self.avatar,
                               destination=self.stock,
                               dt_execution=self.dt_test2,
                               state='done')
        obs = self.Observation.create(state='done',
                                      observed_properties=dict(weight=2.3),
                                      dt_execution=self.dt_test3,
                                      inputs=pre_move.outcomes)
        self.assertEqual(phobj.get_property('weight'), 2.3)
        post_move = self.Operation.Move.create(input=obs.outcome,
                                               destination=outgoing,
                                               dt_execution=self.dt_test3,
                                               state='done')

        # The Observation will be skipped in the reversal plan
        pre_move.plan_revert()
        move_back_1 = self.assert_singleton(post_move.followers)
        self.assertIsInstance(move_back_1, Move)
        move_back_2 = self.assert_singleton(move_back_1.followers)
        self.assertIsInstance(move_back_2, Move)
        self.assertEqual(self.assert_singleton(move_back_2.outcomes).location,
                         self.incoming_loc)
        move_back_1.execute()
        move_back_2.execute()

    def test_done_revert_end_of_chain(self):
        Move = self.Operation.Move
        self.avatar.state = 'present'
        phobj = self.avatar.obj

        pre_move = Move.create(input=self.avatar,
                               destination=self.stock,
                               dt_execution=self.dt_test2,
                               state='done')
        obs = self.Observation.create(state='done',
                                      observed_properties=dict(weight=2.3),
                                      dt_execution=self.dt_test3,
                                      inputs=pre_move.outcomes)
        self.assertEqual(phobj.get_property('weight'), 2.3)

        # The Observation will be skipped in the reversal plan
        pre_move.plan_revert()
        move_back = self.assert_singleton(obs.followers)
        self.assertIsInstance(move_back, Move)
        self.assertEqual(self.assert_singleton(move_back.outcomes).location,
                         self.incoming_loc)
        move_back.execute()

    def test_repr(self):
        dep = self.Observation.create(state='planned',
                                      dt_execution=self.dt_test2,
                                      input=self.avatar)
        repr(dep)
        str(dep)

    def test_create_done_nothing_observed(self):
        self.avatar.state = 'present'
        with self.assertRaises(ObservationError):
            self.Observation.create(state='done',
                                    input=self.avatar)

    def test_create_planned_execute_nothing_observed(self):
        obs = self.Observation.create(state='planned',
                                      dt_execution=self.dt_test2,
                                      input=self.avatar)
        self.avatar.state = 'present'
        with self.assertRaises(ObservationError) as arc:
            obs.execute()
        exc = arc.exception
        self.assertEqual(exc.kwargs['operation'], obs)

    def test_plan_with_result(self):
        self.avatar.state = 'present'
        with self.assertRaises(ObservationError):
            self.Observation.create(state='planned',
                                    dt_execution=self.dt_test2,
                                    observed_properties=dict(qa='ok'),
                                    input=self.avatar)


del WmsTestCaseWithPhysObj
