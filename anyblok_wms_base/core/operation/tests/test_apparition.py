# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from .testcase import WmsTestCase
from anyblok_wms_base.exceptions import (
    OperationIrreversibleError,
    OperationForbiddenState,
    OperationContainerExpected,
)


class TestApparition(WmsTestCase):

    def setUp(self):
        super(TestApparition, self).setUp()
        Wms = self.registry.Wms
        self.goods_type = Wms.Goods.Type.insert(label="My good type",
                                                code='MGT')
        self.stock = self.insert_location('Stock')
        self.Apparition = Wms.Operation.Apparition
        self.Goods = Wms.Goods
        self.Avatar = self.Goods.Avatar

    def test_create_done_one_obliviate(self):
        apparition = self.Apparition.create(
            location=self.stock,
            state='done',
            quantity=1,
            goods_code='x34/7',
            goods_properties=dict(foo=2,
                                  monty='python'),
            goods_type=self.goods_type)
        self.assertEqual(apparition.follows, [])
        avatar = self.assert_singleton(apparition.outcomes)
        goods = avatar.goods
        self.assertEqual(avatar.state, 'present')
        self.assertEqual(avatar.location, self.stock)
        self.assertEqual(goods.type, self.goods_type)
        self.assertEqual(goods.code, 'x34/7')
        self.assertEqual(goods.get_property('foo'), 2)
        self.assertEqual(goods.get_property('monty'), 'python')

        repr(apparition)
        str(apparition)

        apparition.obliviate()
        self.assertEqual(self.Avatar.query().count(), 0)
        self.assertEqual(
            self.Goods.query().filter_by(type=self.goods_type).count(),
            0)

    def test_create_done_several_obliviate(self):
        apparition = self.Apparition.create(
            location=self.stock,
            state='done',
            quantity=3,
            goods_code='x34/7',
            goods_properties=dict(foo=2,
                                  monty='python'),
            goods_type=self.goods_type)
        self.assertEqual(apparition.follows, [])
        avatars = apparition.outcomes
        self.assertEqual(len(avatars), 3)
        for avatar in avatars:
            goods = avatar.goods
            self.assertEqual(avatar.state, 'present')
            self.assertEqual(avatar.location, self.stock)
            self.assertEqual(goods.type, self.goods_type)
            self.assertEqual(goods.code, 'x34/7')
            self.assertEqual(goods.get_property('foo'), 2)
            self.assertEqual(goods.get_property('monty'), 'python')

        # we really have three different Goods, but they share one Property
        # instance
        all_goods = set(av.goods for av in avatars)
        self.assertEqual(len(all_goods), 3)

        all_props = set(g.properties for g in all_goods)
        self.assertEqual(len(all_props), 1)

        repr(apparition)
        str(apparition)

        apparition.obliviate()
        self.assertEqual(self.Avatar.query().count(), 0)
        self.assertEqual(
            self.Goods.query().filter_by(type=self.goods_type).count(),
            0)

    def test_create_done_no_props(self):
        apparition = self.Apparition.create(
            location=self.stock,
            state='done',
            quantity=1,
            goods_code='x34/7',
            goods_type=self.goods_type)
        self.assertEqual(apparition.follows, [])
        avatar = self.assert_singleton(apparition.outcomes)
        goods = avatar.goods
        self.assertEqual(avatar.state, 'present')
        self.assertEqual(avatar.location, self.stock)
        self.assertEqual(goods.type, self.goods_type)
        self.assertEqual(goods.code, 'x34/7')
        self.assertIsNone(goods.properties)

        repr(apparition)
        str(apparition)

    def test_no_revert(self):
        apparition = self.Apparition.create(
            location=self.stock,
            state='done',
            quantity=1,
            goods_code='x34/7',
            goods_type=self.goods_type)
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
                                   goods_code='x34/7',
                                   goods_properties=dict(foo=2,
                                                         monty='python'),
                                   goods_type=self.goods_type)
        exc = arc.exception
        repr(exc)
        str(exc)
        self.assertEqual(exc.kwargs.get('forbidden'), 'planned')

    def test_not_a_container(self):
        wrong_loc = self.Goods.insert(type=self.goods_type)
        with self.assertRaises(OperationContainerExpected) as arc:
            self.Apparition.create(
                location=wrong_loc,
                state='done',
                goods_type=self.goods_type)
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['offender'], wrong_loc)
