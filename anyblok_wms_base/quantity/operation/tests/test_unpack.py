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
        self.Unpack = self.Operation.Unpack
        self.Avatar = self.PhysObj.Avatar

        self.stock = self.insert_location('Stock')
        self.default_quantity_location = self.stock

    def create_packs(self, type_behaviours=None, properties=None, quantity=5):
        self.packed_goods_type = self.PhysObj.Type.insert(
            label="Pack",
            code='PCK',
            behaviours=type_behaviours)
        self.arrival = self.Operation.Arrival.create(
            goods_type=self.packed_goods_type,
            location=self.stock,
            dt_execution=self.dt_test1,
            goods_properties=properties,
            state='planned',
            quantity=quantity)

        self.packs = self.assert_singleton(self.arrival.outcomes)

    def test_whole_done_one_unpacked_type_props(self):
        unpacked_type = self.PhysObj.Type.insert(code='Unpacked')
        self.create_packs(
            type_behaviours=dict(unpack=dict(
                outcomes=[
                    dict(type=unpacked_type.code,
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
            self.PhysObj.query().filter(self.PhysObj.type == unpacked_type))

        self.assertEqual(unpacked_goods.quantity, 15)
        self.assertEqual(unpacked_goods.type, unpacked_type)

    def test_whole_done_one_clone_one_not_clone(self):
        unpacked_clone_type = self.PhysObj.Type.insert(
            code='clone',
            label="Unpacked, clone props")
        unpacked_fwd_type = self.PhysObj.Type.insert(
            code='fwd',
            label="Unpacked, fwd one prop")
        self.create_packs(
            type_behaviours=dict(unpack=dict(
                outcomes=[
                    dict(type='fwd',
                         quantity=3,
                         forward_properties=['foo', 'bar'],
                         required_properties=['foo'],
                         ),
                    dict(type='clone',
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
            self.PhysObj.query().filter(
                self.PhysObj.type == unpacked_clone_type))
        self.assertEqual(unpacked_goods_cloned_props.quantity, 10)
        self.assertEqual(unpacked_goods_cloned_props.properties,
                         self.packs.obj.properties)

        unpacked_goods_fwd_props = self.single_result(
            self.PhysObj.query().filter(
                self.PhysObj.type == unpacked_fwd_type))
        self.assertEqual(unpacked_goods_fwd_props.quantity, 15)
        self.assertNotEqual(unpacked_goods_fwd_props.properties,
                            self.packs.obj.properties)
        self.assertIsNone(unpacked_goods_fwd_props.get_property('other'))
        self.assertEqual(unpacked_goods_fwd_props.get_property('foo'), 3)

    def test_whole_done_one_unpacked_unform(self):
        unpacked_type = self.PhysObj.Type.insert(code='Unpacked')
        self.create_packs(
            type_behaviours=dict(unpack=dict(
                uniform_outcomes=True,
                outcomes=[
                    dict(type=unpacked_type.code,
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

        unpacked_goods = self.single_result(self.PhysObj.query().filter(
            self.PhysObj.type == unpacked_type))

        self.assertEqual(unpacked_goods.quantity, 15)
        self.assertEqual(unpacked_goods.type, unpacked_type)
        self.assertEqual(unpacked_goods.properties,
                         self.packs.obj.properties)

    def test_whole_done_non_uniform(self):
        """Unpack with outcomes defined in pack properties.

        Properties after unpack are forwarded according to configuration
        on the packs' PhysObj Type and on the packs' properties.
        """
        unpacked_type = self.PhysObj.Type.insert(code='Unpacked')
        self.create_packs(
            type_behaviours=dict(unpack=dict(
                forward_properties=['foo', 'bar'],
                required_properties=['foo'],
            )),
            properties=dict(foo=3,
                            baz='second hand',
                            contents=[
                                dict(type=unpacked_type.code,
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

        unpacked_goods = self.PhysObj.query().filter(
            self.PhysObj.type == unpacked_type).all()

        self.assertEqual(len(unpacked_goods), 1)
        unpacked_goods = unpacked_goods[0]
        self.assertEqual(unpacked_goods.quantity, 10)
        self.assertEqual(unpacked_goods.type, unpacked_type)
        self.assertEqual(unpacked_goods.get_property('foo'), 3)
        self.assertEqual(unpacked_goods.get_property('baz'), 'second hand')

    def test_whole_done_non_uniform_local_id(self):
        """Unpack with local_goods_ids in pack properties

        Properties after unpack are forwarded according to configuration
        on the packs' PhysObj Type and on the packs' properties.
        """
        unpacked_type = self.PhysObj.Type.insert(code='Unpacked')
        existing = self.PhysObj.insert(type=unpacked_type, quantity=2)
        existing.set_property('grade', 'best')
        self.create_packs(
            quantity=1,
            type_behaviours=dict(unpack=dict(
                forward_properties=['foo'],
                required_properties=['foo'],
            )),
            properties=dict(foo=3,
                            baz='yes',
                            contents=[
                                dict(type=unpacked_type.code,
                                     quantity=2,
                                     local_goods_ids=[existing.id],
                                     forward_properties=['bar', 'baz']
                                     )
                            ]))
        self.packs.update(state='present')
        unp = self.Unpack.create(quantity=1,
                                 state='done',
                                 dt_execution=self.dt_test2,
                                 input=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        unpacked_goods = self.single_result(
            self.PhysObj.query().filter(self.PhysObj.type == unpacked_type))

        self.assertEqual(unpacked_goods, existing)
        self.assertEqual(unpacked_goods.quantity, 2)
        self.assertEqual(unpacked_goods.type, unpacked_type)
        self.assertEqual(unpacked_goods.get_property('foo'), 3)
        self.assertEqual(unpacked_goods.get_property('baz'), 'yes')
        self.assertEqual(unpacked_goods.get_property('grade'), 'best')

    def test_local_id_several_wrong(self):
        """Unpack with outcomes defined in pack properties, wrong quantity

        Properties after unpack are forwarded according to configuration
        on the packs' PhysObj Type and on the packs' properties.
        """
        unpacked_type = self.PhysObj.Type.insert(code='Unpacked')
        existing = self.PhysObj.insert(type=unpacked_type, quantity=2)
        existing.set_property('grade', 'best')
        self.create_packs(
            quantity=2,
            type_behaviours=dict(unpack=dict(
                forward_properties=['foo'],
                required_properties=['foo'],
            )),
            properties=dict(foo=3,
                            baz='yes',
                            contents=[
                                dict(type=unpacked_type.code,
                                     quantity=2,
                                     local_goods_ids=[existing.id],
                                     forward_properties=['bar', 'baz']
                                     )
                            ]))
        self.packs.update(state='present')
        with self.assertRaises(OperationInputsError) as arc:
            self.Unpack.create(quantity=2,
                               state='done',
                               dt_execution=self.dt_test2,
                               input=self.packs)
        exckw = arc.exception.kwargs
        self.assertEqual(exckw.get('target_qty'), 4)
        self.assertEqual(exckw.get('spec'),
                         dict(type=unpacked_type.code,
                              quantity=2,
                              local_goods_ids=[existing.id],
                              forward_properties=['bar', 'baz', 'foo'],
                              required_properties=['foo']))

    def test_whole_done_one_unpacked_type_missing_props(self):
        unpacked_type = self.PhysObj.Type.insert(code='Unpacked')
        self.create_packs(
            type_behaviours=dict(unpack=dict(
                outcomes=[
                    dict(type=unpacked_type.code,
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
        self.packs.obj.properties = self.PhysObj.Properties.insert(
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
        unpacked_type = self.PhysObj.Type.insert(code='Unpacked')
        self.create_packs(type_behaviours=dict(unpack=dict(
                outcomes=[
                    dict(type=unpacked_type.code,
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

        unpacked_goods = self.PhysObj.query().filter(
            self.PhysObj.type == unpacked_type).all()

        self.assertEqual(len(unpacked_goods), 1)
        unpacked_goods = unpacked_goods[0]
        self.assertEqual(unpacked_goods.quantity, 15)
        self.assertEqual(unpacked_goods.type, unpacked_type)
        self.assertEqual(unpacked_goods.properties, None)

    def test_whole_plan_execute(self):
        """Plan an Unpack (non uniform scenario), then execute it
        """
        unpacked_type = self.PhysObj.Type.insert(code='Unpacked')
        self.create_packs(
            type_behaviours=dict(unpack=dict(
                forward_properties=['foo', 'bar'],
                required_properties=['foo'],
            )),
            properties=dict(foo=3,
                            baz='second hand',
                            contents=[
                                dict(type=unpacked_type.code,
                                     quantity=2,
                                     forward_properties=['bar', 'baz']
                                     )
                            ]))
        unp = self.Unpack.create(quantity=5,
                                 state='planned',
                                 dt_execution=self.dt_test2,
                                 input=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        unpacked_goods = self.single_result(self.PhysObj.query().filter(
            self.PhysObj.type == unpacked_type))

        self.assertEqual(unpacked_goods.quantity, 10)
        self.assertEqual(unpacked_goods.type, unpacked_type)
        self.assertEqual(unpacked_goods.get_property('foo'), 3)
        self.assertEqual(unpacked_goods.get_property('baz'), 'second hand')

        avatar = self.single_result(self.Avatar.query().filter(
            self.Avatar.obj == unpacked_goods))
        self.assertEqual(avatar.state, 'future')
        self.assertEqual(avatar.reason, unp)

        self.assert_quantity(0,
                             goods_type=self.packed_goods_type,
                             at_datetime=self.dt_test2,
                             additional_states=['future'])

        self.packs.state = 'present'
        self.registry.flush()
        unp.execute()
        self.assertEqual(avatar.state, 'present')
        self.assertEqual(self.packs.state, 'past')
        self.assertEqual(self.packs.reason, unp)

        self.assert_quantity(0,
                             goods_type=self.packed_goods_type,
                             at_datetime=self.dt_test2,
                             additional_states=['future'])
        self.assertEqual(
            self.Avatar.query().join(self.Avatar.obj).filter(
                self.PhysObj.type == self.packed_goods_type,
                self.Avatar.state == 'future').count(),
            0)

    def test_partial_plan_execute(self):
        """Plan a partial Unpack (uniform scenario), then execute it
        """
        unpacked_type = self.PhysObj.Type.insert(code='Unpacked')
        self.create_packs(
            type_behaviours=dict(unpack=dict(
                uniform_outcomes=True,
                outcomes=[
                    dict(type=unpacked_type.code,
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

        PhysObj = self.PhysObj
        unpacked_goods = self.single_result(
            PhysObj.query().filter(PhysObj.type == unpacked_type))

        self.assertEqual(unpacked_goods.quantity, 24)
        self.assertEqual(unpacked_goods.type, unpacked_type)
        self.assertEqual(unpacked_goods.get_property('foo'), 7)

        avatar = self.single_result(
            self.Avatar.query().filter(self.Avatar.obj == unpacked_goods))
        self.assertEqual(avatar.reason, unp)
        self.assertEqual(avatar.state, 'future')

        self.assert_quantity(1,
                             goods_type=self.packed_goods_type,
                             additional_states=['future'],
                             at_datetime=self.dt_test2)

        self.packs.state = 'present'
        unp.execute(dt_execution=self.dt_test3)

        PhysObj, Avatar = self.PhysObj, self.Avatar

        # not unpacked
        packs_goods_query = PhysObj.query().filter(
            PhysObj.type == self.packed_goods_type)
        still_packed = self.single_result(
            packs_goods_query.join(Avatar.obj).filter(
                Avatar.state == 'present'))
        self.assertEqual(still_packed.quantity, 1)

        # check intermediate objects no leftover intermediate packs
        after_split = self.single_result(
            Avatar.query().join(Avatar.obj).filter(
                PhysObj.type == self.packed_goods_type,
                Avatar.state == 'past',
                Avatar.reason == unp))
        self.assertEqual(after_split.obj.quantity, 4)
        self.assertEqual(
            PhysObj.query().join(Avatar.obj).filter(
                Avatar.state == 'future').count(),
            0)

    def test_partial_cancel(self):
        """Plan a partial Unpack (uniform scenario), then cancel it
        """
        unpacked_type = self.PhysObj.Type.insert(code='Unpacked')
        self.create_packs(
            type_behaviours=dict(unpack=dict(
                uniform_outcomes=True,
                outcomes=[
                    dict(type=unpacked_type.code,
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
        PhysObj = self.PhysObj
        self.assertEqual(
            PhysObj.query().filter(PhysObj.type == unpacked_type).count(),
            0)
        self.assert_quantity(5,
                             goods_type=self.packed_goods_type,
                             additional_states=['future'],
                             at_datetime=self.dt_test2)

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
        unpacked_type = self.PhysObj.Type.insert(code='Unpacked')
        self.create_packs(
            type_behaviours=dict(unpack=dict(
                uniform_outcomes=True,
                outcomes=[
                    dict(type=unpacked_type.code,
                         quantity=6,
                         ),
                ]),
            ),
            properties={})
        unp = self.Unpack.create(quantity=5, state='planned', input=self.packs,
                                 dt_execution=self.dt_test2)
        repr(unp)
        str(unp)
