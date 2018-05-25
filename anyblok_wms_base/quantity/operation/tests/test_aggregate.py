# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta
from anyblok_wms_base.testing import WmsTestCase
from anyblok_wms_base.exceptions import (
    OperationInputsError,
    OperationInputWrongState,
    OperationMissingInputsError,
)
from anyblok_wms_base.constants import (
    SPLIT_AGGREGATE_PHYSICAL_BEHAVIOUR
)


class TestAggregate(WmsTestCase):

    def setUp(self):
        super(TestAggregate, self).setUp()
        Wms = self.registry.Wms
        Operation = Wms.Operation
        self.goods_type = Wms.Goods.Type.insert(label="My good type",
                                                code="MyGT")
        self.loc = Wms.Location.insert(label="Incoming location")

        # The arrival fields doesn't matter, we'll insert goods directly
        self.arrival = Operation.Arrival.insert(goods_type=self.goods_type,
                                                location=self.loc,
                                                state='planned',
                                                dt_execution=self.dt_test1,
                                                quantity=17)

        Avatar = Wms.Goods.Avatar
        self.avatars = [
            Avatar.insert(goods=Wms.Goods.insert(quantity=qty,
                                                 type=self.goods_type),
                          location=self.loc,
                          dt_from=self.dt_test1,
                          state='future',
                          reason=self.arrival)
            for qty in (1, 2)]
        self.Agg = Operation.Aggregate
        self.Goods = Wms.Goods

    def plan_aggregate(self):
        return self.Agg.create(inputs=self.avatars,
                               state='planned',
                               dt_execution=self.dt_test2)

    def assertQuantity(self, quantity, **kwargs):
        self.assertEqual(
            self.loc.quantity(self.goods_type, **kwargs),
            quantity)

    def test_create_done_same_props(self):
        props = self.Goods.Properties.insert(flexible=dict(foo='bar'))
        for avatar in self.avatars:
            avatar.state = 'present'
            avatar.goods.properties = props
        agg = self.Agg.create(inputs=self.avatars, state='done')
        self.assertEqual(agg.inputs, self.avatars)
        for record in self.avatars:
            self.assertEqual(record.state, 'past')
            self.assertEqual(record.reason, agg)
        new_avatar = self.assert_singleton(agg.outcomes)
        self.assertEqual(new_avatar.location, self.loc)
        new_goods = new_avatar.goods
        self.assertEqual(new_goods.properties, props)
        self.assertEqual(new_goods.quantity, 3)

        for dt in (self.dt_test1, self.dt_test2, self.dt_test3):
            self.assertQuantity(3, at_datetime=dt,
                                additional_states=('past', 'future'))

    def test_create_done_equal_props(self):
        """Test equality check for different records of properties."""
        for avatar in self.avatars:
            avatar.state = 'present'
            props = self.Goods.Properties.insert(flexible=dict(foo='bar'))
            avatar.goods.properties = props
        agg = self.Agg.create(inputs=self.avatars, state='done')

        new_avatar = self.assert_singleton(agg.outcomes)
        self.assertEqual(new_avatar.location, self.loc)
        new_goods = new_avatar.goods
        self.assertIsNotNone(new_goods.properties)
        new_props = new_goods.properties.to_dict()
        new_props.pop('id')
        old_props = props.to_dict()
        old_props.pop('id')
        self.assertEqual(new_props, old_props)

    def test_create_done_several_dt_from(self):
        self.avatars[1].dt_from = self.dt_test2
        for record in self.avatars:
            record.state = 'present'
        agg = self.Agg.create(inputs=self.avatars, state='done',
                              dt_execution=self.dt_test3)
        for record in self.avatars:
            self.assertEqual(record.dt_until, self.dt_test3)
        outcome = self.assert_singleton(agg.outcomes)
        self.assertEqual(outcome.state, 'present')
        self.assertEqual(outcome.dt_from, self.dt_test3)

    def assertBackToBeginning(self, state='present', props=None):
        new_goods = self.Goods.query().all()
        self.assertEqual(len(new_goods), 2)
        if props is not None:
            old_props = props.to_dict()
            old_props.pop('id')
            for line in new_goods:
                self.assertIsNotNone(line.properties)
                new_props = line.properties.to_dict()
                new_props.pop('id')
                self.assertEqual(new_props, old_props)
        self.assertEqual(set(g.quantity for g in new_goods), set((1, 2)))

        for avatar in self.Goods.Avatar.query().all():
            self.assertEqual(avatar.goods.type, self.goods_type)
            self.assertEqual(avatar.location, self.loc)
            self.assertEqual(avatar.state, 'present')
            self.assertEqual(avatar.reason, self.arrival)

    def test_create_done_equal_props_obliviate(self):
        for avatar in self.avatars:
            avatar.state = 'present'
            props = self.Goods.Properties.insert(flexible=dict(foo='bar'))
            avatar.goods.properties = props
        agg = self.Agg.create(inputs=self.avatars, state='done')
        agg.obliviate()
        self.assertBackToBeginning(state='present', props=props)

    def test_create_done_several_follows_obliviate(self):
        """Test that oblivion doesn't shuffle original reasons.

        TODO this test has one chance over 2 to pass by accident.
        make a better one, and label it as a MultipleGoods mixin test, by
        issuing more goods and reasons and pairing them randomly so that
        chances of passing by coincidence are really low.
        """
        for record in self.avatars:
            record.state = 'present'
        Operation = self.registry.Wms.Operation
        other_reason = Operation.Arrival.insert(goods_type=self.goods_type,
                                                location=self.loc,
                                                state='done',
                                                dt_execution=self.dt_test1,
                                                quantity=35)
        self.avatars[0].reason = other_reason
        agg = self.Agg.create(inputs=self.avatars, state='done',
                              dt_execution=self.dt_test2)
        self.assertEqual(set(agg.follows), set((self.arrival, other_reason)))
        agg.obliviate()
        new_avatars = self.Goods.Avatar.query().all()
        self.assertEqual(len(new_avatars), 2)
        for avatar in new_avatars:
            if avatar.goods.quantity == 1:
                exp_reason = other_reason
            else:
                exp_reason = self.arrival
            self.assertEqual(avatar.reason, exp_reason)

        # CASCADE options did the necessary cleanups
        self.assertEqual(Operation.HistoryInput.query().count(), 0)

    def test_forbid_differences_avatars(self):
        """Forbid differences among avatars own fields"""
        other_loc = self.registry.Wms.Location.insert(label="Other location")
        self.avatars[1].location = other_loc
        with self.assertRaises(OperationInputsError) as arc:
            self.plan_aggregate()
        exc = arc.exception
        diff = exc.kwargs.get('diff')
        self.assertIsNotNone(diff)
        self.assertEqual(set(diff.get('location')),
                         set((other_loc, self.loc)))

    def test_forbid_differences_goods(self):
        """Forbid differences among avatars' Goods."""
        self.avatars[0].goods.code = 'AB'
        self.avatars[1].goods.code = 'CD'
        with self.assertRaises(OperationInputsError) as arc:
            self.plan_aggregate()
        exc = arc.exception
        diff = exc.kwargs.get('diff')
        self.assertIsNotNone(diff)
        self.assertEqual(set(diff.get('code')),
                         set(('AB', 'CD')))

    def test_ensure_goods(self):
        with self.assertRaises(OperationMissingInputsError):
            self.Agg.create(state='planned', dt_execution=self.dt_test2)
        self.avatars = []
        with self.assertRaises(OperationMissingInputsError):
            self.plan_aggregate()

    def test_create_done_ensure_goods_present(self):
        # nowadays, this just tests the base Operation class
        with self.assertRaises(OperationInputWrongState) as arc:
            self.Agg.create(inputs=self.avatars, state='done',
                            dt_execution=self.dt_test1)

        exc_kwargs = arc.exception.kwargs
        self.assertEqual(exc_kwargs.get('inputs'), self.avatars)
        self.assertTrue(exc_kwargs.get('record') in self.avatars)

        self.avatars[0].state = 'present'
        with self.assertRaises(OperationInputsError) as arc:
            self.Agg.create(inputs=self.avatars, state='done')

        exc_kwargs = arc.exception.kwargs
        self.assertEqual(exc_kwargs.get('inputs'), self.avatars)
        self.assertEqual(exc_kwargs.get('record'), self.avatars[1])

    def test_execute_ensure_goods_present(self):
        # nowadays, this just tests the base Operation class
        agg = self.plan_aggregate()
        with self.assertRaises(OperationInputWrongState) as arc:
            agg.execute()
        exc_kwargs = arc.exception.kwargs
        self.assertEqual(exc_kwargs.get('inputs'), self.avatars)
        self.assertTrue(exc_kwargs.get('record') in self.avatars)

        self.avatars[0].state = 'present'
        with self.assertRaises(OperationInputWrongState) as arc:
            agg.execute()

        exc_kwargs = arc.exception.kwargs
        self.assertEqual(exc_kwargs.get('inputs'), self.avatars)
        self.assertEqual(exc_kwargs.get('record'), self.avatars[1])

    def test_execute(self):
        # TODO the test fails if properties are linked to self.avatars
        # records after creation of the operation, and that's actually
        # a problem for all SingleGoods and MultipleGoods operations
        # (link to properties created or changed after the op creation)
        props = self.Goods.Properties.insert(flexible=dict(foo='bar'))
        for avatar in self.avatars:
            avatar.state = 'present'
            avatar.goods.properties = props

        agg = self.plan_aggregate()
        self.assertEqual(agg.inputs, self.avatars)
        self.assertQuantity(3)
        for dt in (self.dt_test1, self.dt_test2, self.dt_test3):
            self.assertQuantity(3, at_datetime=dt,
                                additional_states=('past', 'future'))

        agg.execute(dt_execution=self.dt_test3)

        self.assertQuantity(3)
        for dt in (self.dt_test1, self.dt_test2, self.dt_test3):
            self.assertQuantity(3, at_datetime=dt,
                                additional_states=('past', 'future'))

        for record in self.avatars:
            self.assertEqual(record.state, 'past')
            self.assertEqual(record.reason, agg)

        Avatar = self.Goods.Avatar
        new_avatar = self.assert_singleton(
            Avatar.query().filter(
                Avatar.reason == agg,
                Avatar.state == 'present').all())
        self.assertEqual(new_avatar.goods.quantity, 3)
        self.assertEqual(new_avatar.location, self.loc)
        self.assertEqual(new_avatar.goods.properties, props)

    def test_execute_several_dt_from(self):
        self.avatars[1].dt_from = self.dt_test2
        dt_test4 = self.dt_test3 + timedelta(1)

        agg = self.Agg.create(inputs=self.avatars, state='planned',
                              dt_execution=self.dt_test3)
        for record in self.avatars:
            self.assertEqual(record.dt_until, self.dt_test3)
        outcome = self.assert_singleton(agg.outcomes)
        self.assertEqual(outcome.dt_from, self.dt_test3)

        for record in self.avatars:
            record.state = 'present'

        agg.execute(dt_execution=dt_test4)
        for record in self.avatars:
            self.assertEqual(record.dt_until, dt_test4)
            self.assertEqual(record.state, 'past')
        self.assertEqual(outcome.dt_from, dt_test4)

    def test_execute_obliviate(self):
        props = self.Goods.Properties.insert(flexible=dict(foo='bar'))
        for avatar in self.avatars:
            avatar.state = 'present'
            avatar.goods.properties = props

        agg = self.plan_aggregate()
        self.assertEqual(agg.inputs, self.avatars)

        agg.execute()
        agg.obliviate()
        self.assertBackToBeginning(state='present', props=props)

    def test_cancel(self):
        agg = self.plan_aggregate()
        self.assertEqual(agg.inputs, self.avatars)

        agg.cancel()
        self.assertEqual(self.Agg.query().count(), 0)
        Avatar = self.Goods.Avatar
        all_avatars = Avatar.query().join(Avatar.goods).filter(
            self.Goods.type == self.avatars[0].goods.type).all()
        self.assertEqual(set(all_avatars), set(self.avatars))

        all_goods = self.Goods.query().filter(
            self.Goods.type == self.avatars[0].goods.type).all()
        self.assertEqual(set(all_goods), set(av.goods for av in self.avatars))

    def test_reversibility(self):
        for record in self.avatars:
            record.state = 'present'
        agg = self.Agg.create(inputs=self.avatars, state='done')

        self.assertTrue(agg.is_reversible())
        gt = self.avatars[0].goods.type
        gt.behaviours = {SPLIT_AGGREGATE_PHYSICAL_BEHAVIOUR: True}
        self.assertFalse(agg.is_reversible())

        gt.behaviours['aggregate'] = dict(reversible=True)
        self.assertTrue(agg.is_reversible())
