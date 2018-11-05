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
    OperationIrreversibleError,
    OperationForbiddenState,
    OperationContainerExpected,
)


class TestApparition(WmsTestCase):

    def setUp(self):
        super(TestApparition, self).setUp()
        Wms = self.registry.Wms
        self.physobj_type = Wms.PhysObj.Type.insert(label="My good type",
                                                    code='MGT')
        self.stock = self.insert_location('Stock')
        self.Apparition = Wms.Operation.Apparition
        self.PhysObj = Wms.PhysObj
        self.Avatar = self.PhysObj.Avatar

    def test_create_done_one_obliviate(self):
        apparition = self.Apparition.create(
            location=self.stock,
            state='done',
            quantity=1,
            physobj_code='x34/7',
            physobj_properties=dict(foo=2,
                                    monty='python'),
            physobj_type=self.physobj_type)
        self.assertEqual(len(apparition.follows), 0)
        avatar = self.assert_singleton(apparition.outcomes)
        goods = avatar.obj
        self.assertEqual(avatar.state, 'present')
        self.assertEqual(avatar.location, self.stock)
        self.assertEqual(goods.type, self.physobj_type)
        self.assertEqual(goods.code, 'x34/7')
        self.assertEqual(goods.get_property('foo'), 2)
        self.assertEqual(goods.get_property('monty'), 'python')

        repr(apparition)
        str(apparition)

        apparition.obliviate()
        self.assertEqual(self.Avatar.query().count(), 0)
        self.assertEqual(
            self.PhysObj.query().filter_by(type=self.physobj_type).count(),
            0)

    def test_create_done_several_obliviate(self):
        apparition = self.Apparition.create(
            location=self.stock,
            state='done',
            quantity=3,
            physobj_code='x34/7',
            physobj_properties=dict(foo=2,
                                    monty='python'),
            physobj_type=self.physobj_type)
        self.assertEqual(len(apparition.follows), 0)
        avatars = apparition.outcomes
        self.assertEqual(len(avatars), 3)
        for avatar in avatars:
            goods = avatar.obj
            self.assertEqual(avatar.state, 'present')
            self.assertEqual(avatar.location, self.stock)
            self.assertEqual(goods.type, self.physobj_type)
            self.assertEqual(goods.code, 'x34/7')
            self.assertEqual(goods.get_property('foo'), 2)
            self.assertEqual(goods.get_property('monty'), 'python')

        # we really have three different PhysObj, but they share one Property
        # instance
        all_goods = set(av.obj for av in avatars)
        self.assertEqual(len(all_goods), 3)

        all_props = set(g.properties for g in all_goods)
        self.assertEqual(len(all_props), 1)

        repr(apparition)
        str(apparition)

        apparition.obliviate()
        self.assertEqual(self.Avatar.query().count(), 0)
        self.assertEqual(
            self.PhysObj.query().filter_by(type=self.physobj_type).count(),
            0)

    def test_create_done_no_props(self):
        apparition = self.Apparition.create(
            location=self.stock,
            state='done',
            quantity=1,
            physobj_code='x34/7',
            physobj_type=self.physobj_type)
        self.assertEqual(len(apparition.follows), 0)
        avatar = self.assert_singleton(apparition.outcomes)
        goods = avatar.obj
        self.assertEqual(avatar.state, 'present')
        self.assertEqual(avatar.location, self.stock)
        self.assertEqual(goods.type, self.physobj_type)
        self.assertEqual(goods.code, 'x34/7')
        self.assertIsNone(goods.properties)

        repr(apparition)
        str(apparition)

    def test_no_revert(self):
        apparition = self.Apparition.create(
            location=self.stock,
            state='done',
            quantity=1,
            physobj_code='x34/7',
            physobj_type=self.physobj_type)
        with self.assertRaises(OperationIrreversibleError) as arc:
            apparition.plan_revert()

        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.operation, apparition)

    def test_no_planned_state(self):
        with self.assertRaises(OperationForbiddenState) as arc:
            self.Apparition.create(location=self.stock,
                                   state='planned',
                                   dt_execution=self.dt_test1,
                                   physobj_code='x34/7',
                                   physobj_properties=dict(foo=2,
                                                           monty='python'),
                                   physobj_type=self.physobj_type)
        exc = arc.exception
        repr(exc)
        str(exc)
        self.assertEqual(exc.kwargs.get('forbidden'), 'planned')

    def test_not_a_container(self):
        wrong_loc = self.PhysObj.insert(type=self.physobj_type)
        with self.assertRaises(OperationContainerExpected) as arc:
            self.Apparition.create(
                location=wrong_loc,
                state='done',
                physobj_type=self.physobj_type)
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['offender'], wrong_loc)

    def check_compatibility_goods_col(self, suffix, update_value):
        """Test compatibility function field for the rename goods->obj.

        To be removed together with that function field once the deprecation
        has expired.
        """
        old_field_name = 'goods_' + suffix
        new_field_name = 'physobj_' + suffix
        app = self.Apparition.create(location=self.stock,
                                     state='done',
                                     quantity=1,
                                     dt_execution=self.dt_test1,
                                     physobj_code='765',
                                     physobj_properties=dict(foo=5,
                                                             bar='monty'),
                                     physobj_type=self.physobj_type)

        def assert_warnings_goods_deprecation(got_warnings):
            self.assert_warnings_deprecation(
                got_warnings, "'%s'" % old_field_name,
                "rename to '%s'" % new_field_name)

        with warnings.catch_warnings(record=True) as got:
            # reading
            self.assertEqual(getattr(app, old_field_name),
                             getattr(app, new_field_name))
        assert_warnings_goods_deprecation(got)

        with warnings.catch_warnings(record=True) as got:
            app.update(**{old_field_name: update_value})
        assert_warnings_goods_deprecation(got)
        self.assertEqual(getattr(app, new_field_name), update_value)

        with warnings.catch_warnings(record=True) as got:
            # querying
            self.assert_singleton(
                self.Apparition.query().filter_by(
                    **{old_field_name: update_value}).all(),
                value=app)
        assert_warnings_goods_deprecation(got)

    def test_compatibility_goods_code(self):
        self.check_compatibility_goods_col('code', 'ABC')

    def test_compatibility_goods_properties(self):
        self.check_compatibility_goods_col('properties', dict(foo=7))

    def test_compatibility_goods_type(self):
        pot = self.PhysObj.Type.insert(code='OTHER')
        self.check_compatibility_goods_col('type', pot)
