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
    OperationInputsError,
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
        self.goods_type = Wms.Goods.Type.insert(label="My good type")
        self.loc = Wms.Location.insert(label="Incoming location")

        # The arrival fields doesn't matter, we'll insert goods directly
        self.arrival = Operation.Arrival.insert(goods_type=self.goods_type,
                                                location=self.loc,
                                                state='planned',
                                                dt_execution=self.dt_test1,
                                                quantity=17)

        self.goods = [Wms.Goods.insert(quantity=qty,
                                       type=self.goods_type,
                                       location=self.loc,
                                       dt_from=self.dt_test1,
                                       state='future',
                                       reason=self.arrival)
                      for qty in (1, 2)]
        self.Agg = Operation.Aggregate
        self.Goods = Wms.Goods

    def plan_aggregate(self):
        return self.Agg.create(inputs=self.goods,
                               state='planned',
                               dt_execution=self.dt_test2)

    def assertQuantity(self, quantity, **kwargs):
        self.assertEqual(
            self.loc.quantity(self.goods_type, **kwargs),
            quantity)

    def test_create_done_same_props(self):
        props = self.Goods.Properties.insert(flexible=dict(foo='bar'))
        for record in self.goods:
            record.update(state='present', properties=props)
        agg = self.Agg.create(inputs=self.goods, state='done')
        self.assertEqual(agg.inputs, self.goods)
        for record in self.goods:
            self.assertEqual(record.state, 'past')
            self.assertEqual(record.reason, agg)
        new_goods = self.Goods.query().filter(
            self.Goods.reason == agg,
            self.Goods.state == 'present').all()
        self.assertEqual(len(new_goods), 1)
        new_goods = new_goods[0]
        self.assertEqual(new_goods.quantity, 3)
        self.assertEqual(new_goods.location, self.loc)
        self.assertEqual(new_goods.properties, props)

        for dt in (self.dt_test1, self.dt_test2, self.dt_test3):
            self.assertQuantity(3, at_datetime=dt)

    def test_create_done_equal_props(self):
        """Test equality check for different records of properties."""
        for record in self.goods:
            props = self.Goods.Properties.insert(flexible=dict(foo='bar'))
            record.update(state='present', properties=props)
        agg = self.Agg.create(inputs=self.goods, state='done')
        new_goods = self.Goods.query().filter(
            self.Goods.reason == agg,
            self.Goods.state == 'present').all()
        self.assertEqual(len(new_goods), 1)
        new_goods = new_goods[0]
        new_props = new_goods.properties.to_dict()
        new_props.pop('id')
        old_props = props.to_dict()
        old_props.pop('id')
        self.assertEqual(new_props, old_props)

    def test_create_done_several_dt_from(self):
        self.goods[1].dt_from = self.dt_test2
        for record in self.goods:
            record.state = 'present'
        agg = self.Agg.create(inputs=self.goods, state='done',
                              dt_execution=self.dt_test3)
        for record in self.goods:
            self.assertEqual(record.dt_until, self.dt_test3)
        outcome = self.single_result(
            self.Goods.query().filter(self.Goods.reason == agg,
                                      self.Goods.state == 'present'))
        self.assertEqual(outcome.dt_from, self.dt_test3)

    def assertBackToBeginning(self, state='present', props=None):
        new_goods = self.Goods.query().filter().all()
        self.assertEqual(len(new_goods), 2)
        if props is not None:
            old_props = props.to_dict()
            old_props.pop('id')
            for line in new_goods:
                new_props = line.properties.to_dict()
                new_props.pop('id')
                self.assertEqual(new_props, old_props)

        for line in new_goods:
            self.assertEqual(line.type, self.goods_type)
            self.assertEqual(line.location, self.loc)
            self.assertEqual(line.state, 'present')
            self.assertEqual(line.reason, self.arrival)
        self.assertEqual(set(line.quantity for line in new_goods), set((1, 2)))

    def test_create_done_equal_props_obliviate(self):
        for record in self.goods:
            props = self.Goods.Properties.insert(flexible=dict(foo='bar'))
            record.update(state='present', properties=props)
        agg = self.Agg.create(inputs=self.goods, state='done')
        agg.obliviate()
        self.assertBackToBeginning(state='present', props=props)

    def test_create_done_several_follows_obliviate(self):
        """Test that oblivion doesn't shuffle original reasons.

        TODO this test has one chance over 2 to pass by accident.
        make a better one, and label it as a MultipleGoods mixin test, by
        issuing more goods and reasons and pairing them randomly so that
        chances of passing by coincidence are really low.
        """
        for record in self.goods:
            record.state = 'present'
        Operation = self.registry.Wms.Operation
        other_reason = Operation.Arrival.insert(goods_type=self.goods_type,
                                                location=self.loc,
                                                state='done',
                                                dt_execution=self.dt_test1,
                                                quantity=35)
        self.goods[0].reason = other_reason
        agg = self.Agg.create(inputs=self.goods, state='done',
                              dt_execution=self.dt_test2)
        self.assertEqual(set(agg.follows), set((self.arrival, other_reason)))
        agg.obliviate()
        new_goods = self.Goods.query().filter().all()
        self.assertEqual(len(new_goods), 2)
        for goods in new_goods:
            exp_reason = other_reason if goods.quantity == 1 else self.arrival
            self.assertEqual(goods.reason, exp_reason)

        # CASCADE options did the necessary cleanups
        self.assertEqual(Operation.WorkingOn.query().count(), 0)

    def test_forbid_differences(self):
        other_loc = self.registry.Wms.Location.insert(label="Other location")
        self.goods[1].location = other_loc
        with self.assertRaises(OperationInputsError) as arc:
            self.plan_aggregate()
        exc = arc.exception
        self.assertEqual(exc.kwargs.get('field'), 'location')
        self.assertSetEqual(set((exc.kwargs.get('first_field'),
                                 exc.kwargs.get('second_field'))),
                            set((other_loc, self.loc)))

    def test_ensure_goods(self):
        with self.assertRaises(OperationMissingInputsError):
            self.Agg.create(state='planned', dt_execution=self.dt_test2)
        self.goods = []
        with self.assertRaises(OperationMissingInputsError):
            self.plan_aggregate()

    def test_create_done_ensure_goods_present(self):
        with self.assertRaises(OperationInputsError) as arc:
            self.Agg.create(inputs=self.goods, state='done',
                            dt_execution=self.dt_test1)

        exc_kwargs = arc.exception.kwargs
        self.assertEqual(exc_kwargs.get('goods'), self.goods)
        self.assertTrue(exc_kwargs.get('record') in self.goods)

        self.goods[0].state = 'present'
        with self.assertRaises(OperationInputsError) as arc:
            self.Agg.create(inputs=self.goods, state='done')

        exc_kwargs = arc.exception.kwargs
        self.assertEqual(exc_kwargs.get('goods'), self.goods)
        self.assertEqual(exc_kwargs.get('record'), self.goods[1])

    def test_execute_ensure_goods_present(self):
        agg = self.plan_aggregate()
        with self.assertRaises(OperationInputsError) as arc:
            agg.execute()
        exc_kwargs = arc.exception.kwargs
        self.assertEqual(exc_kwargs.get('goods'), self.goods)
        self.assertTrue(exc_kwargs.get('record') in self.goods)

        self.goods[0].state = 'present'
        with self.assertRaises(OperationInputsError) as arc:
            agg.execute()

        exc_kwargs = arc.exception.kwargs
        self.assertEqual(exc_kwargs.get('goods'), self.goods)
        self.assertEqual(exc_kwargs.get('record'), self.goods[1])

    def test_execute(self):
        # TODO the test fails if properties are linked to self.goods
        # records after creation of the operation, and that's actually
        # a problem for all SingleGoods and MultipleGoods operations
        # (link to properties created or changed after the op creation)
        props = self.Goods.Properties.insert(flexible=dict(foo='bar'))
        for record in self.goods:
            record.update(state='present', properties=props)

        agg = self.plan_aggregate()
        self.assertEqual(agg.inputs, self.goods)

        for dt in (self.dt_test1, self.dt_test2, self.dt_test3):
            self.assertQuantity(3, at_datetime=dt)

        agg.execute(dt_execution=self.dt_test3)

        for dt in (self.dt_test1, self.dt_test2, self.dt_test3):
            self.assertQuantity(3, at_datetime=dt)

        for record in self.goods:
            self.assertEqual(record.state, 'past')
            self.assertEqual(record.reason, agg)
        new_goods = self.Goods.query().filter(
            self.Goods.reason == agg,
            self.Goods.state == 'present').all()
        self.assertEqual(len(new_goods), 1)
        new_goods = new_goods[0]
        self.assertEqual(new_goods.quantity, 3)
        self.assertEqual(new_goods.location, self.loc)
        self.assertEqual(new_goods.properties, props)

    def test_execute_several_dt_from(self):
        self.goods[1].dt_from = self.dt_test2
        dt_test4 = self.dt_test3 + timedelta(1)

        agg = self.Agg.create(inputs=self.goods, state='planned',
                              dt_execution=self.dt_test3)
        for record in self.goods:
            self.assertEqual(record.dt_until, self.dt_test3)
        outcome = self.single_result(
            self.Goods.query().filter(self.Goods.reason == agg))
        self.assertEqual(outcome.dt_from, self.dt_test3)

        for record in self.goods:
            record.state = 'present'

        agg.execute(dt_execution=dt_test4)
        for record in self.goods:
            self.assertEqual(record.dt_until, dt_test4)
            self.assertEqual(record.state, 'past')
        self.assertEqual(outcome.dt_from, dt_test4)

    def test_execute_obliviate(self):
        props = self.Goods.Properties.insert(flexible=dict(foo='bar'))
        for record in self.goods:
            record.update(state='present', properties=props)

        agg = self.plan_aggregate()
        self.assertEqual(agg.inputs, self.goods)

        agg.execute()
        agg.obliviate()
        self.assertBackToBeginning(state='present', props=props)

    def test_cancel(self):
        agg = self.plan_aggregate()
        self.assertEqual(agg.inputs, self.goods)

        agg.cancel()
        self.assertEqual(self.Agg.query().count(), 0)
        all_goods = self.Goods.query().filter(
            self.Goods.type == self.goods[0].type).all()
        self.assertEqual(set(all_goods), set(self.goods))

    def test_reversibility(self):
        for record in self.goods:
            record.state = 'present'
        agg = self.Agg.create(inputs=self.goods, state='done')

        self.assertTrue(agg.is_reversible())
        gt = self.goods[0].type
        gt.behaviours = {SPLIT_AGGREGATE_PHYSICAL_BEHAVIOUR: True}
        self.assertFalse(agg.is_reversible())

        gt.behaviours['aggregate'] = dict(reversible=True)
        self.assertTrue(agg.is_reversible())
