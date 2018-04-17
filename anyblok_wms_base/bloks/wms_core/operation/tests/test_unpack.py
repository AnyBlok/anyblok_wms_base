# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCase
from anyblok_wms_base.exceptions import (
    OperationInputsError,
)


class TestUnpack(WmsTestCase):

    def setUp(self):
        super(TestUnpack, self).setUp()
        Wms = self.registry.Wms
        self.Operation = Operation = Wms.Operation
        self.Unpack = Operation.Unpack
        self.Goods = Wms.Goods
        self.Avatar = Wms.Goods.Avatar

        self.stock = Wms.Location.insert(label="Stock")

    def create_packs(self, type_behaviours=None, properties=None):
        self.packed_goods_type = self.Goods.Type.insert(
            label="Pack",
            behaviours=type_behaviours)
        self.arrival = self.Operation.Arrival.create(
            goods_type=self.packed_goods_type,
            location=self.stock,
            dt_execution=self.dt_test1,
            goods_properties=properties,
            state='planned')

        self.packs = self.assert_singleton(self.arrival.outcomes)

    def assert_goods_records(self, count, goods_type):
        """Assert count of Goods with given type and return them.

        This is primarily meant for Goods produced by the Unpack
        """
        records = self.Goods.query().filter(
            self.Goods.type == goods_type).all()
        self.assertEqual(len(records), count)
        return records

    def single_avatar(self, goods):
        return self.single_result(
            self.Avatar.query().filter(self.Avatar.goods == goods))

    def test_done_one_unpacked_type_props(self):
        unpacked_type = self.Goods.Type.insert(label="Unpacked")
        self.create_packs(
            type_behaviours=dict(unpack=dict(
                outcomes=[
                    dict(type=unpacked_type.id,
                         quantity=3,
                         forward_properties=['foo', 'bar'],
                         required_properties=['foo'],
                         )
                ],
            )),
            properties=dict(foo=3),
            )
        self.packs.update(state='present')
        unp = self.Unpack.create(state='done',
                                 dt_execution=self.dt_test2,
                                 input=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        for unpacked_goods in self.assert_goods_records(3, unpacked_type):
            self.assertEqual(unpacked_goods.type, unpacked_type)

    def test_done_clone_one_not_clone(self):
        unpacked_clone_type = self.Goods.Type.insert(
            label="Unpacked, clone props")
        unpacked_fwd_type = self.Goods.Type.insert(
            label="Unpacked, fwd one prop")
        self.create_packs(
            type_behaviours=dict(unpack=dict(
                outcomes=[
                    dict(type=unpacked_fwd_type.id,
                         quantity=3,
                         forward_properties=['foo', 'bar'],
                         required_properties=['foo'],
                         ),
                    dict(type=unpacked_clone_type.id,
                         quantity=2,
                         forward_properties='clone'
                         )
                ],
            )),
            properties=dict(foo=3, other='xyz'),
            )
        self.packs.update(state='present')
        unp = self.Unpack.create(state='done',
                                 dt_execution=self.dt_test2,
                                 input=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        for goods in self.assert_goods_records(2, unpacked_clone_type):
            self.assertEqual(goods.properties,
                             self.packs.goods.properties)

        for goods in self.assert_goods_records(3, unpacked_fwd_type):
            self.assertNotEqual(goods.properties,
                                self.packs.goods.properties)
            self.assertIsNone(goods.get_property('other'))
            self.assertEqual(goods.get_property('foo'), 3)

    def test_done_one_unpacked_type_uniform(self):
        unpacked_type = self.Goods.Type.insert(label="Unpacked")
        self.create_packs(
            type_behaviours=dict(unpack=dict(
                uniform_outcomes=True,
                outcomes=[
                    dict(type=unpacked_type.id,
                         quantity=3,
                         )
                ],
            )),
            properties=dict(foo=3, po_ref='ABC'),
            )
        self.packs.update(state='present')
        unp = self.Unpack.create(state='done',
                                 dt_execution=self.dt_test2,
                                 input=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        for goods in self.assert_goods_records(3, unpacked_type):
            self.assertEqual(goods.properties,
                             self.packs.goods.properties)

    def test_done_non_uniform(self):
        """Unpack with outcomes defined in pack properties.

        Properties after unpack are forwarded according to configuration
        on the packs' Goods Type and on the packs' properties.
        """
        unpacked_type = self.Goods.Type.insert(label="Unpacked")
        self.create_packs(
            type_behaviours=dict(unpack=dict(
                forward_properties=['foo', 'bar'],
                required_properties=['foo'],
            )),
            properties=dict(foo=3,
                            baz='second hand',
                            unpack_outcomes=[
                                dict(type=unpacked_type.id,
                                     quantity=2,
                                     forward_properties=['bar', 'baz']
                                     )
                            ]))
        self.packs.update(state='present')
        unp = self.Unpack.create(state='done',
                                 dt_execution=self.dt_test2,
                                 input=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        for unpacked_goods in self.assert_goods_records(2, unpacked_type):
            self.assertEqual(unpacked_goods.type, unpacked_type)
            self.assertEqual(unpacked_goods.get_property('foo'), 3)
            self.assertEqual(unpacked_goods.get_property('baz'), 'second hand')

    def test_done_one_unpacked_type_missing_props(self):
        unpacked_type = self.Goods.Type.insert(label="Unpacked")
        self.create_packs(
            type_behaviours=dict(unpack=dict(
                outcomes=[
                    dict(type=unpacked_type.id,
                         quantity=3,
                         forward_properties=['foo', 'bar'],
                         required_properties=['foo'],
                         )
                ],
            )),
            )

        def unpack():
            self.packs.update(state='present')
            self.Unpack.create(state='done',
                               dt_execution=self.dt_test2,
                               input=self.packs)

        # No property at all, we fail explicitely
        with self.assertRaises(OperationInputsError) as arc:
            unpack()
        str(arc.exception)
        repr(arc.exception)
        exc_kwargs = arc.exception.kwargs
        self.assertEqual(list(exc_kwargs.get('inputs')), [self.packs])
        self.assertEqual(exc_kwargs.get('req_props'), ['foo'])
        self.assertEqual(exc_kwargs.get('type'), self.packed_goods_type)
        # we also have an 'operation' kwarg, because that exc is raised
        # after actual instantiation, but we can't test it because
        # we don't have a create() returned value to compare

        # Having properties, still missing the required one
        self.packs.goods.properties = self.Goods.Properties.insert(
            flexible=dict(bar=1))

        with self.assertRaises(OperationInputsError) as arc:
            unpack()
        str(arc.exception)
        repr(arc.exception)
        exc_kwargs = arc.exception.kwargs
        self.assertEqual(list(exc_kwargs.get('inputs')), [self.packs])
        self.assertEqual(exc_kwargs.get('prop'), 'foo')

    def test_done_one_unpacked_type_no_props(self):
        """Unpacking operation, forwarding no properties."""
        unpacked_type = self.Goods.Type.insert(label="Unpacked")
        self.create_packs(type_behaviours=dict(unpack=dict(
                outcomes=[
                    dict(type=unpacked_type.id,
                         quantity=3,
                         )
                ]
        )))
        self.packs.update(state='present')
        unp = self.Unpack.create(state='done',
                                 dt_execution=self.dt_test2,
                                 input=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        for unpacked_goods in self.assert_goods_records(3, unpacked_type):
            self.assertEqual(unpacked_goods.type, unpacked_type)
            self.assertEqual(unpacked_goods.properties, None)

            avatar = self.single_avatar(unpacked_goods)
            self.assertEqual(avatar.state, 'present')
            self.assertEqual(avatar.reason, unp)

    def test_plan_execute(self):
        """Plan an Unpack (non uniform scenario), then execute it
        """
        unpacked_type = self.Goods.Type.insert(label="Unpacked")
        self.create_packs(
            type_behaviours=dict(unpack=dict(
                forward_properties=['foo', 'bar'],
                required_properties=['foo'],
            )),
            properties=dict(foo=3,
                            baz='second hand',
                            unpack_outcomes=[
                                dict(type=unpacked_type.id,
                                     quantity=2,
                                     forward_properties=['bar', 'baz']
                                     )
                            ]))
        unp = self.Unpack.create(state='planned',
                                 dt_execution=self.dt_test2,
                                 input=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        self.assertEqual(len(unp.outcomes), 2)
        for unpacked_goods in self.assert_goods_records(2, unpacked_type):
            self.assertEqual(unpacked_goods.type, unpacked_type)
            self.assertEqual(unpacked_goods.get_property('foo'), 3)
            self.assertEqual(unpacked_goods.get_property('baz'), 'second hand')

            avatar = self.single_avatar(unpacked_goods)
            self.assertEqual(avatar.state, 'future')
            self.assertEqual(avatar.reason, unp)

        self.assertEqual(
            self.stock.quantity(self.packed_goods_type,
                                at_datetime=self.dt_test2,
                                additional_states=['future']),
            0)

        self.packs.state = 'present'
        self.registry.flush()
        unp.execute()
        for avatar in unp.outcomes:
            self.assertEqual(avatar.state, 'present')
        self.assertEqual(self.packs.state, 'past')
        self.assertEqual(self.packs.reason, unp)

        self.assertEqual(
            self.stock.quantity(self.packed_goods_type,
                                at_datetime=self.dt_test2,
                                additional_states=['future']),
            0)
        self.assertEqual(
            self.Avatar.query().join(self.Avatar.goods).filter(
                self.Goods.type == self.packed_goods_type,
                self.Avatar.state == 'future').count(),
            0)

    def test_no_outcomes(self):
        """Unpacking with no outcomes should be hard errors."""
        self.create_packs(
            type_behaviours=dict(unpack=dict(outcomes=[])),
        )
        self.packs.update(state='present')
        with self.assertRaises(OperationInputsError) as arc:
            self.Unpack.create(state='done',
                               dt_execution=self.dt_test2,
                               input=self.packs)
        str(arc.exception)
        repr(arc.exception)
        exc_kwargs = arc.exception.kwargs
        self.assertEqual(exc_kwargs.get('type'), self.packed_goods_type)
        self.assertEqual(list(exc_kwargs.get('inputs')), [self.packs])
        self.assertEqual(exc_kwargs.get('behaviour'), dict(outcomes=[]))
        self.assertEqual(exc_kwargs.get('specific'), ())
        # we also have an 'operation' kwarg, because that exc is raised
        # after actual instantiation, but we can't test it because
        # we don't have a create() returned value to compare

    def test_no_behaviour(self):
        """Unpacking with no specified 'unpack' behaviour is an error."""
        self.create_packs(
            type_behaviours=dict(other_op=[]),
        )
        self.packs.update(state='present')
        with self.assertRaises(OperationInputsError) as arc:
            self.Unpack.create(state='done',
                               dt_execution=self.dt_test2,
                               input=self.packs)
        str(arc.exception)
        repr(arc.exception)
        exc_kwargs = arc.exception.kwargs
        self.assertEqual(exc_kwargs.get('type'), self.packed_goods_type)
        self.assertEqual(list(exc_kwargs.get('inputs')), [self.packs])

    def test_repr(self):
        unpacked_type = self.Goods.Type.insert(label="Unpacked")
        self.create_packs(
            type_behaviours=dict(unpack=dict(
                uniform_outcomes=True,
                outcomes=[
                    dict(type=unpacked_type.id,
                         quantity=6,
                         ),
                ]),
            ),
            properties={})
        unp = self.Unpack.create(state='planned', input=self.packs,
                                 dt_execution=self.dt_test2)
        repr(unp)
        str(unp)
