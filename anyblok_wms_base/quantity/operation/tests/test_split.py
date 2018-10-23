# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCaseWithPhysObj

from anyblok_wms_base.constants import (
    SPLIT_AGGREGATE_PHYSICAL_BEHAVIOUR
    )
from anyblok_wms_base.exceptions import (
    OperationError,
    OperationIrreversibleError,
    )


class TestSplit(WmsTestCaseWithPhysObj):
    """Specific testing of Wms.Operation.Split

    This may look very partial, but most of the testing of Split is
    actually done within the tests of operations that inherit from the
    PhysObjSplitter mixin.

    TODO for the sake of clarity and granularity of tests, complete this
    testcase so that Split can have an independent development life.
    """

    arrival_kwargs = dict(quantity=3)
    """Used in setUpSharedData()."""

    def test_create_done(self):
        self.avatar.state = 'present'
        split = self.Operation.Split.create(state='done',
                                            input=self.avatar,
                                            dt_execution=self.dt_test2,
                                            quantity=2)

        outcomes = split.outcomes
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(self.avatar.state, 'past')
        self.assertEqual(self.avatar.dt_from, self.dt_test1)
        self.assertEqual(self.avatar.dt_until, self.dt_test2)
        self.assertEqual(sum(out.obj.quantity for out in outcomes), 3)
        for outcome in outcomes:
            self.assertEqual(outcome.dt_from, self.dt_test2)
            self.assertEqual(outcome.location, self.incoming_loc)
            self.assertEqual(outcome.state, 'present')
            self.assertEqual(outcome.obj.type, self.physobj_type)
            # No need to test quantity > 0, we now have a constraint on that

    def test_create_planned_execute(self):
        self.avatar.state = 'present'
        split = self.Operation.Split.create(state='planned',
                                            input=self.avatar,
                                            dt_execution=self.dt_test2,
                                            quantity=2)

        all_outcomes = split.outcomes

        self.assertEqual(len(all_outcomes), 2)

        self.assertEqual(self.avatar.state, 'present')
        self.assertEqual(self.avatar.dt_from, self.dt_test1)
        self.assertEqual(self.avatar.dt_until, self.dt_test2)
        self.assertEqual(sum(out.obj.quantity for out in all_outcomes), 3)
        # this will fail if me mangle the datetimes severely
        self.assertEqual(
            self.Wms.quantity(location=self.incoming_loc,
                              goods_type=self.physobj_type,
                              additional_states=['future'],
                              at_datetime=self.dt_test3),
            3)

        for outcome in all_outcomes:
            self.assertEqual(outcome.dt_from, self.dt_test2)
            self.assertEqual(outcome.location, self.incoming_loc)
            self.assertEqual(outcome.state, 'future')
            self.assertEqual(outcome.obj.type, self.physobj_type)
        wished_outcome = split.wished_outcome
        self.assertEqual(wished_outcome.obj.quantity, 2)
        self.assertTrue(wished_outcome in all_outcomes)

        split.execute(self.dt_test2)
        for outcome in all_outcomes:
            self.assertEqual(outcome.dt_from, self.dt_test2)
            self.assertEqual(outcome.dt_until, None)
            self.assertEqual(outcome.location, self.incoming_loc)
            self.assertEqual(outcome.state, 'present')
            self.assertEqual(outcome.obj.type, self.physobj_type)

        # whatever the time we pick at the total quantity should still be
        # unchanged (using the right states, of course)
        for add_states, dt in ((None, None),
                               (['future'], self.dt_test2),
                               (['future'], self.dt_test3),
                               (['past'], self.dt_test1),
                               (['past'], self.dt_test2),
                               (['past'], self.dt_test3)):
            self.assertEqual(
                self.Wms.quantity(location=self.incoming_loc,
                                  goods_type=self.physobj_type,
                                  additional_states=add_states,
                                  at_datetime=dt),
                3)

    def test_create_planned_outcome_disappears(self):
        split = self.Operation.Split.create(state='planned',
                                            input=self.avatar,
                                            dt_execution=self.dt_test2,
                                            quantity=2)

        split.wished_outcome.delete()
        with self.assertRaises(OperationError):
            split.wished_outcome

    def test_irreversible(self):
        """A case in which Splits are irreversible."""
        self.physobj_type.behaviours = {
            SPLIT_AGGREGATE_PHYSICAL_BEHAVIOUR: True}
        # if that fails, then the issue is not in Split implementation:
        self.assertEqual(self.physobj_type.is_split_reversible(), False)

        self.avatar.state = 'present'
        split = self.Operation.Split.create(state='done',
                                            input=self.avatar,
                                            quantity=2)
        self.assertFalse(split.is_reversible())

        # This actually implemented by the Operation base class:
        with self.assertRaises(OperationIrreversibleError) as arc:
            split.plan_revert()
        exc = arc.exception
        str(exc)
        self.assertEqual(exc.kwargs.get('op'), split)

    def test_revert_final(self):
        """Test reversal of a Split that's the latest operation on goods.

        Starting point of the test is exactly the same as in
        :meth:`test_create_done`, we don't repeat assertions about that.
        """
        self.avatar.state = 'present'
        split = self.Operation.Split.create(state='done',
                                            input=self.avatar,
                                            dt_execution=self.dt_test2,
                                            quantity=2)

        outcomes = split.outcomes
        split.plan_revert(dt_execution=self.dt_test3)
        aggregate = self.single_result(self.Operation.Aggregate.query())
        self.assertEqual(set(aggregate.inputs), set(outcomes))
        aggregate.execute()

        Avatar = self.PhysObj.Avatar
        new_avatar = self.single_result(
            Avatar.query().filter(Avatar.state == 'present'))
        new_goods = new_avatar.obj
        self.assertEqual(new_goods.quantity, 3)
        # TODO would be neat for the outcome to actually be self.physobj,
        # i.e., the PhysObj record we started with
        self.assertEqual(new_avatar.location, self.avatar.location)
        self.assertEqual(new_goods.type, self.physobj.type)
        self.assertEqual(new_goods.properties, self.physobj.properties)

        # TODO we might actually want in case Splits have no meaning
        # in real life to simply forget an end-of-chain Split.

        # no weird leftovers
        self.assertEqual(Avatar.query().filter_by(state='future').count(), 0)

    def test_revert_implicit_intermediate(self):
        """Test reversal of a Split that's been inserted implictely.
        """
        self.avatar.state = 'present'
        move = self.Operation.Move.create(state='done',
                                          destination=self.stock,
                                          input=self.avatar,
                                          quantity=2)

        split = self.assert_singleton(move.follows)
        self.assertEqual(move.input.outcome_of, split)

        aggregate, rev_leafs = split.plan_revert()
        self.assertEqual(len(rev_leafs), 1)
        rev_move = rev_leafs[0]

        self.assert_singleton(rev_move.follows, value=move)
        rev_move.execute()
        aggregate.execute()

        Avatar = self.PhysObj.Avatar
        new_avatar = self.single_result(
            Avatar.query().filter(Avatar.state == 'present'))
        new_goods = new_avatar.obj
        self.assertEqual(new_goods.quantity, 3)
        # TODO would be neat for the outcome to actually be self.physobj,
        # i.e., the PhysObj record we started with
        self.assertEqual(new_avatar.location, self.avatar.location)
        self.assertEqual(new_goods.type, self.physobj.type)
        self.assertEqual(new_goods.properties, self.physobj.properties)

        # no weird leftovers
        self.assertEqual(
            Avatar.query().filter(Avatar.state == 'future').count(), 0)

    def test_obliviate_final(self):
        """Test oblivion of a Split that's the latest operation on goods.

        Starting point of the test is exactly the same as in
        :meth:`test_create_done`, we don't repeat assertions about that.
        """
        self.avatar.state = 'present'
        split = self.Operation.Split.create(state='done',
                                            input=self.avatar,
                                            quantity=2)

        split.obliviate()
        Avatar = self.PhysObj.Avatar
        restored_avatar = self.single_result(Avatar.query())
        restored_goods = self.single_result(self.PhysObj.query().filter_by(
            type=self.physobj.type))
        self.assertEqual(restored_avatar.obj, restored_goods)

        self.assertEqual(restored_avatar.location, self.avatar.location)
        # TODO would be neat for the outcome to actually be self.physobj,
        # i.e., the PhysObj record we started with
        self.assertEqual(restored_goods, self.physobj)
        self.assertEqual(restored_goods.quantity, 3)
        self.assertEqual(restored_goods.properties, self.physobj.properties)


del WmsTestCaseWithPhysObj
