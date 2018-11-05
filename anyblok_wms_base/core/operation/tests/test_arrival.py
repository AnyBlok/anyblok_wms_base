# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
import warnings
from anyblok_wms_base.testing import WmsTestCase

from anyblok_wms_base.exceptions import (
    OperationContainerExpected,
)


class TestArrival(WmsTestCase):

    def setUp(self):
        super(TestArrival, self).setUp()
        PhysObj = self.PhysObj
        self.goods_type = PhysObj.Type.insert(label="My good type",
                                              code='MGT')
        self.incoming_loc = self.insert_location('INCOMING')
        self.stock = self.insert_location('STOCK')

        self.Arrival = self.Operation.Arrival
        self.Avatar = self.PhysObj.Avatar

    def test_create_planned_execute(self):
        arrival = self.Arrival.create(location=self.incoming_loc,
                                      state='planned',
                                      dt_execution=self.dt_test1,
                                      goods_code='765',
                                      goods_properties=dict(foo=5,
                                                            bar='monty'),
                                      goods_type=self.goods_type)
        self.assertEqual(len(arrival.follows), 0)
        avatar = self.assert_singleton(arrival.outcomes)
        goods = avatar.obj
        self.assertEqual(avatar.state, 'future')
        self.assertEqual(avatar.location, self.incoming_loc)
        self.assertEqual(goods.type, self.goods_type)
        self.assertEqual(goods.code, '765')
        self.assertEqual(goods.get_property('foo'), 5)
        self.assertEqual(goods.get_property('bar'), 'monty')
        self.assertEqual(avatar.dt_from, self.dt_test1)

        arrival.execute(self.dt_test2)
        self.assertEqual(arrival.state, 'done')
        self.assertEqual(arrival.dt_execution, self.dt_test2)
        self.assertEqual(arrival.dt_start, self.dt_test2)
        self.assertEqual(avatar.state, 'present')
        self.assertEqual(goods.get_property('foo'), 5)
        self.assertEqual(goods.get_property('bar'), 'monty')
        self.assertEqual(goods.code, '765')
        self.assertEqual(avatar.dt_from, self.dt_test2)

    def test_create_done(self):
        arrival = self.Arrival.create(location=self.incoming_loc,
                                      state='done',
                                      goods_code='x34/7',
                                      goods_properties=dict(foo=2,
                                                            monty='python'),
                                      goods_type=self.goods_type)
        self.assertEqual(len(arrival.follows), 0)
        avatar = self.assert_singleton(arrival.outcomes)
        goods = avatar.obj
        self.assertEqual(avatar.state, 'present')
        self.assertEqual(avatar.location, self.incoming_loc)
        self.assertEqual(goods.type, self.goods_type)
        self.assertEqual(goods.code, 'x34/7')
        self.assertEqual(goods.get_property('foo'), 2)
        self.assertEqual(goods.get_property('monty'), 'python')

    def check_compatibility_goods_col(self, suffix, update_value):
        """Test compatibility function field for the rename goods->obj.

        To be removed together with that function field once the deprecation
        has expired.
        """
        old_field_name = 'goods_' + suffix
        new_field_name = 'physobj_' + suffix
        arrival = self.Arrival.create(location=self.incoming_loc,
                                      state='planned',
                                      dt_execution=self.dt_test1,
                                      physobj_code='765',
                                      physobj_properties=dict(foo=5,
                                                              bar='monty'),
                                      physobj_type=self.goods_type)

        def assert_warnings_goods_deprecation(got_warnings):
            self.assert_warnings_deprecation(
                got_warnings, "'%s'" % old_field_name,
                "rename to '%s'" % new_field_name)

        with warnings.catch_warnings(record=True) as got:
            # reading
            self.assertEqual(getattr(arrival, old_field_name),
                             getattr(arrival, new_field_name))
        assert_warnings_goods_deprecation(got)

        with warnings.catch_warnings(record=True) as got:
            arrival.update(**{old_field_name: update_value})
        assert_warnings_goods_deprecation(got)
        self.assertEqual(getattr(arrival, new_field_name), update_value)

        with warnings.catch_warnings(record=True) as got:
            # querying
            self.assert_singleton(
                self.Arrival.query().filter_by(
                    **{old_field_name: update_value}).all(),
                value=arrival)
        assert_warnings_goods_deprecation(got)

    def test_compatibility_goods_code(self):
        self.check_compatibility_goods_col('code', 'ABC')

    def test_compatibility_goods_properties(self):
        self.check_compatibility_goods_col('properties', dict(foo=7))

    def test_compatibility_goods_type(self):
        pot = self.PhysObj.Type.insert(code='OTHER')
        self.check_compatibility_goods_col('type', pot)

    def test_arrival_done_obliviate(self):
        arrival = self.Arrival.create(location=self.incoming_loc,
                                      state='done',
                                      goods_code='x34/7',
                                      goods_properties=dict(foo=2,
                                                            monty='python'),
                                      goods_type=self.goods_type)
        arrival.obliviate()
        self.assertEqual(self.Avatar.query().count(), 0)
        self.assertEqual(
            self.PhysObj.query().filter_by(type=self.goods_type).count(), 0)

    def test_arrival_planned_execute_obliviate(self):
        arrival = self.Arrival.create(location=self.incoming_loc,
                                      state='planned',
                                      dt_execution=self.dt_test1,
                                      goods_code='x34/7',
                                      goods_properties=dict(foo=2,
                                                            monty='python'),
                                      goods_type=self.goods_type)
        arrival.execute()
        arrival.obliviate()
        self.assertEqual(self.Avatar.query().count(), 0)
        self.assertEqual(
            self.PhysObj.query().filter_by(type=self.goods_type).count(), 0)

    def test_repr(self):
        arrival = self.Arrival(location=self.incoming_loc,
                               state='done',
                               goods_code='x34/7',
                               goods_properties=dict(foo=2,
                                                     monty='python'),
                               goods_type=self.goods_type)
        repr(arrival)
        str(arrival)

    def test_not_a_container(self):
        wrong_loc = self.PhysObj.insert(type=self.goods_type)
        with self.assertRaises(OperationContainerExpected) as arc:
            self.Arrival.create(
                location=wrong_loc,
                state='done',
                goods_type=self.goods_type)
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['offender'], wrong_loc)
