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
            state='planned',
            quantity=5)

        self.packs = self.assert_singleton(self.arrival.outcomes)

    def test_whole_done_one_unpacked_type_props(self):
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
        unp = self.Unpack.create(quantity=5,
                                 state='done',
                                 dt_execution=self.dt_test2,
                                 input=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        unpacked_goods = self.single_result(
            self.Goods.query().filter(self.Goods.type == unpacked_type))

        self.assertEqual(unpacked_goods.quantity, 15)
        self.assertEqual(unpacked_goods.type, unpacked_type)

    def test_whole_done_one_clone_one_not_clone(self):
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
        unp = self.Unpack.create(quantity=5,
                                 state='done',
                                 dt_execution=self.dt_test2,
                                 input=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        unpacked_goods_cloned_props = self.single_result(
            self.Goods.query().filter(self.Goods.type == unpacked_clone_type))
        self.assertEqual(unpacked_goods_cloned_props.quantity, 10)
        self.assertEqual(unpacked_goods_cloned_props.properties,
                         self.packs.goods.properties)

        unpacked_goods_fwd_props = self.single_result(
            self.Goods.query().filter(self.Goods.type == unpacked_fwd_type))
        self.assertEqual(unpacked_goods_fwd_props.quantity, 15)
        self.assertNotEqual(unpacked_goods_fwd_props.properties,
                            self.packs.goods.properties)
        self.assertIsNone(unpacked_goods_fwd_props.get_property('other'))
        self.assertEqual(unpacked_goods_fwd_props.get_property('foo'), 3)

    def test_whole_done_one_unpacked_unform(self):
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
        unp = self.Unpack.create(quantity=5,
                                 state='done',
                                 dt_execution=self.dt_test2,
                                 input=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        unpacked_goods = self.single_result(self.Goods.query().filter(
            self.Goods.type == unpacked_type))

        self.assertEqual(unpacked_goods.quantity, 15)
        self.assertEqual(unpacked_goods.type, unpacked_type)
        self.assertEqual(unpacked_goods.properties,
                         self.packs.goods.properties)

    def test_whole_done_non_uniform(self):
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
        unp = self.Unpack.create(quantity=5,
                                 state='done',
                                 dt_execution=self.dt_test2,
                                 input=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        unpacked_goods = self.Goods.query().filter(
            self.Goods.type == unpacked_type).all()

        self.assertEqual(len(unpacked_goods), 1)
        unpacked_goods = unpacked_goods[0]
        self.assertEqual(unpacked_goods.quantity, 10)
        self.assertEqual(unpacked_goods.type, unpacked_type)
        self.assertEqual(unpacked_goods.get_property('foo'), 3)
        self.assertEqual(unpacked_goods.get_property('baz'), 'second hand')

    def test_whole_done_one_unpacked_type_missing_props(self):
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
            self.Unpack.create(quantity=5,
                               state='done',
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

    def test_whole_done_one_unpacked_type_no_props(self):
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
        unp = self.Unpack.create(quantity=5,
                                 state='done',
                                 dt_execution=self.dt_test2,
                                 input=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        unpacked_goods = self.Goods.query().filter(
            self.Goods.type == unpacked_type).all()

        self.assertEqual(len(unpacked_goods), 1)
        unpacked_goods = unpacked_goods[0]
        self.assertEqual(unpacked_goods.quantity, 15)
        self.assertEqual(unpacked_goods.type, unpacked_type)
        self.assertEqual(unpacked_goods.properties, None)

    def test_whole_plan_execute(self):
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
        unp = self.Unpack.create(quantity=5,
                                 state='planned',
                                 dt_execution=self.dt_test2,
                                 input=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        unpacked_goods = self.single_result(self.Goods.query().filter(
            self.Goods.type == unpacked_type))

        self.assertEqual(unpacked_goods.quantity, 10)
        self.assertEqual(unpacked_goods.type, unpacked_type)
        self.assertEqual(unpacked_goods.get_property('foo'), 3)
        self.assertEqual(unpacked_goods.get_property('baz'), 'second hand')

        avatar = self.single_result(self.Avatar.query().filter(
            self.Avatar.goods == unpacked_goods))
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

    def test_partial_plan_execute(self):
        """Plan a partial Unpack (uniform scenario), then execute it
        """
        unpacked_type = self.Goods.Type.insert(label="Unpacked")
        self.create_packs(
            type_behaviours=dict(unpack=dict(
                uniform_outcomes=True,
                outcomes=[
                    dict(type=unpacked_type.id,
                         quantity=6,
                         ),
                ],
            )),
            properties=dict(foo=7))

        unp = self.Unpack.create(quantity=4,
                                 state='planned',
                                 dt_execution=self.dt_test2,
                                 input=self.packs)
        self.assertEqual(unp.follows[0].type, 'wms_split')
        self.assertEqual(unp.partial, True)

        Goods = self.Goods
        unpacked_goods = self.single_result(
            Goods.query().filter(Goods.type == unpacked_type))

        self.assertEqual(unpacked_goods.quantity, 24)
        self.assertEqual(unpacked_goods.type, unpacked_type)
        self.assertEqual(unpacked_goods.get_property('foo'), 7)

        avatar = self.single_result(
            self.Avatar.query().filter(self.Avatar.goods == unpacked_goods))
        self.assertEqual(avatar.reason, unp)
        self.assertEqual(avatar.state, 'future')

        self.assertEqual(
            self.stock.quantity(self.packed_goods_type,
                                additional_states=['future'],
                                at_datetime=self.dt_test2), 1)

        self.packs.state = 'present'
        unp.execute(dt_execution=self.dt_test3)

        Goods, Avatar = self.Goods, self.Avatar

        # not unpacked
        packs_goods_query = Goods.query().filter(
            Goods.type == self.packed_goods_type)
        still_packed = self.single_result(
            packs_goods_query.join(Avatar.goods).filter(
                Avatar.state == 'present'))
        self.assertEqual(still_packed.quantity, 1)

        # check intermediate objects no leftover intermediate packs
        after_split = self.single_result(
            Avatar.query().join(Avatar.goods).filter(
                Goods.type == self.packed_goods_type,
                Avatar.state == 'past',
                Avatar.reason == unp))
        self.assertEqual(after_split.goods.quantity, 4)
        self.assertEqual(
            Goods.query().join(Avatar.goods).filter(
                Avatar.state == 'future').count(),
            0)

    def test_partial_cancel(self):
        """Plan a partial Unpack (uniform scenario), then cancel it
        """
        unpacked_type = self.Goods.Type.insert(label="Unpacked")
        self.create_packs(
            type_behaviours=dict(unpack=dict(
                uniform_outcomes=True,
                outcomes=[
                    dict(type=unpacked_type.id,
                         quantity=6,
                         ),
                ],
            )),
            properties=dict(foo=7))

        unp = self.Unpack.create(quantity=4,
                                 state='planned',
                                 dt_execution=self.dt_test2,
                                 input=self.packs)
        self.assertEqual(unp.follows[0].type, 'wms_split')
        self.assertEqual(unp.partial, True)

        unp.cancel()
        Goods = self.Goods
        self.assertEqual(
            Goods.query().filter(Goods.type == unpacked_type).count(),
            0)
        self.assertEqual(
            self.stock.quantity(self.packed_goods_type,
                                additional_states=['future'],
                                at_datetime=self.dt_test2),
            5)

    def test_no_outcomes(self):
        """Unpacking with no outcomes should be hard errors."""
        self.create_packs(
            type_behaviours=dict(unpack=dict(outcomes=[])),
        )
        self.packs.update(state='present')
        with self.assertRaises(OperationInputsError) as arc:
            self.Unpack.create(quantity=5,
                               state='done',
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
            self.Unpack.create(quantity=5,
                               state='done',
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
        unp = self.Unpack.create(quantity=5, state='planned', input=self.packs,
                                 dt_execution=self.dt_test2)
        repr(unp)
        str(unp)
