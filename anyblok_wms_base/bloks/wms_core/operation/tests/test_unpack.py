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
    OperationGoodsError,
)


class TestUnpack(WmsTestCase):

    def setUp(self):
        super(TestUnpack, self).setUp()
        Wms = self.registry.Wms
        self.Operation = Operation = Wms.Operation
        self.Unpack = Operation.Unpack
        self.Goods = Wms.Goods

        self.stock = Wms.Location.insert(label="Stock")

    def create_packs(self, type_behaviours=None, properties=None):
        self.packed_goods_type = self.Goods.Type.insert(
            label="Pack",
            behaviours=type_behaviours)
        goods_type = self.Goods.Type.insert(label="My good type")

        self.arrival = self.Operation.Arrival.insert(
            goods_type=goods_type,
            location=self.stock,
            dt_execution=self.dt_test1,
            state='planned',
            quantity=3)

        if properties is None:
            props = None
        else:
            props = self.Goods.Properties.insert(**properties)
        self.packs = self.Goods.insert(quantity=5,
                                       type=self.packed_goods_type,
                                       location=self.stock,
                                       dt_from=self.dt_test1,
                                       state='future',
                                       properties=props,
                                       reason=self.arrival)

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
            properties=dict(flexible=dict(foo=3)),
            )
        self.packs.update(state='present')
        unp = self.Unpack.create(quantity=5,
                                 state='done',
                                 dt_execution=self.dt_test2,
                                 goods=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        unpacked_goods = self.Goods.query().filter(
            self.Goods.type == unpacked_type).all()

        self.assertEqual(len(unpacked_goods), 1)
        unpacked_goods = unpacked_goods[0]
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
            properties=dict(flexible=dict(foo=3, other='xyz')),
            )
        self.packs.update(state='present')
        unp = self.Unpack.create(quantity=5,
                                 state='done',
                                 dt_execution=self.dt_test2,
                                 goods=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        unpacked_goods_cloned_props = self.Goods.query().filter(
            self.Goods.type == unpacked_clone_type).all()
        self.assertEqual(len(unpacked_goods_cloned_props), 1)
        unpacked_goods_cloned_props = unpacked_goods_cloned_props[0]
        self.assertEqual(unpacked_goods_cloned_props.quantity, 10)
        self.assertEqual(unpacked_goods_cloned_props.properties,
                         self.packs.properties)

        unpacked_goods_fwd_props = self.Goods.query().filter(
            self.Goods.type == unpacked_fwd_type).all()
        self.assertEqual(len(unpacked_goods_fwd_props), 1)
        unpacked_goods_fwd_props = unpacked_goods_fwd_props[0]
        self.assertEqual(unpacked_goods_fwd_props.quantity, 15)
        self.assertNotEqual(unpacked_goods_fwd_props.properties,
                            self.packs.properties)
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
            properties=dict(flexible=dict(foo=3, po_ref='ABC')),
            )
        self.packs.update(state='present')
        unp = self.Unpack.create(quantity=5,
                                 state='done',
                                 dt_execution=self.dt_test2,
                                 goods=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        unpacked_goods = self.Goods.query().filter(
            self.Goods.type == unpacked_type).all()

        self.assertEqual(len(unpacked_goods), 1)
        unpacked_goods = unpacked_goods[0]
        self.assertEqual(unpacked_goods.quantity, 15)
        self.assertEqual(unpacked_goods.type, unpacked_type)
        self.assertEqual(unpacked_goods.properties, self.packs.properties)

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
            properties=dict(
                flexible=dict(foo=3,
                              baz='second hand',
                              unpack_outcomes=[
                                  dict(type=unpacked_type.id,
                                       quantity=2,
                                       forward_properties=['bar', 'baz']
                                       )
                                  ])))
        self.packs.update(state='present')
        unp = self.Unpack.create(quantity=5,
                                 state='done',
                                 dt_execution=self.dt_test2,
                                 goods=self.packs)
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
                               goods=self.packs)

        # No property at all, we fail explicitely
        with self.assertRaises(OperationGoodsError) as arc:
            unpack()
        str(arc.exception)
        repr(arc.exception)
        self.assertEqual(arc.exception.kwargs,
                         dict(packs=self.packs,
                              req_props=['foo'],
                              type=self.packed_goods_type))

        # Having properties, still missing the required one
        self.packs.properties = self.Goods.Properties.insert(
            flexible=dict(bar=1))

        with self.assertRaises(OperationGoodsError) as arc:
            unpack()
        str(arc.exception)
        repr(arc.exception)
        self.assertEqual(arc.exception.kwargs, dict(prop='foo',
                                                    packs=self.packs))

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
                                 goods=self.packs)
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
            properties=dict(
                flexible=dict(foo=3,
                              baz='second hand',
                              unpack_outcomes=[
                                  dict(type=unpacked_type.id,
                                       quantity=2,
                                       forward_properties=['bar', 'baz']
                                       )
                                  ])))
        unp = self.Unpack.create(quantity=5,
                                 state='planned',
                                 dt_execution=self.dt_test2,
                                 goods=self.packs)
        self.assertEqual(unp.follows, [self.arrival])

        unpacked_goods = self.Goods.query().filter(
            self.Goods.type == unpacked_type).all()

        self.assertEqual(len(unpacked_goods), 1)
        unpacked_goods = unpacked_goods[0]
        self.assertEqual(unpacked_goods.quantity, 10)
        self.assertEqual(unpacked_goods.state, 'future')
        self.assertEqual(unpacked_goods.type, unpacked_type)
        self.assertEqual(unpacked_goods.get_property('foo'), 3)
        self.assertEqual(unpacked_goods.get_property('baz'), 'second hand')
        self.assertEqual(unpacked_goods.reason, unp)

        self.assertEqual(
            self.stock.quantity(self.packed_goods_type,
                                at_datetime=self.dt_test2,
                                goods_state='future'),
            0)

        self.packs.state = 'present'
        self.registry.flush()
        unp.execute()
        self.assertEqual(unpacked_goods.state, 'present')
        self.assertEqual(self.packs.state, 'past')
        self.assertEqual(self.packs.reason, unp)

        self.assertEqual(
            self.stock.quantity(self.packed_goods_type,
                                at_datetime=self.dt_test2,
                                goods_state='future'),
            0)
        self.assertEqual(
            self.Goods.query().filter(
                self.Goods.type == self.packed_goods_type,
                self.Goods.state == 'future').count(),
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
            properties=dict(flexible=dict(foo=7)))

        unp = self.Unpack.create(quantity=4,
                                 state='planned',
                                 dt_execution=self.dt_test2,
                                 goods=self.packs)
        self.assertEqual(unp.follows[0].type, 'wms_split')
        self.assertEqual(unp.partial, True)

        Goods = self.Goods
        unpacked_goods = Goods.query().filter(
            Goods.type == unpacked_type).all()

        self.assertEqual(len(unpacked_goods), 1)
        unpacked_goods = unpacked_goods[0]
        self.assertEqual(unpacked_goods.reason, unp)
        self.assertEqual(unpacked_goods.quantity, 24)
        self.assertEqual(unpacked_goods.state, 'future')
        self.assertEqual(unpacked_goods.type, unpacked_type)
        self.assertEqual(unpacked_goods.get_property('foo'), 7)

        self.assertEqual(
            self.stock.quantity(self.packed_goods_type,
                                goods_state='future',
                                at_datetime=self.dt_test2), 1)

        self.packs.state = 'present'
        packs_query = self.Goods.query().filter(
            self.Goods.type == self.packed_goods_type)
        unp.execute(dt_execution=self.dt_test3)

        # not unpacked
        still_packed = self.single_result(
            packs_query.filter(Goods.state == 'present'))
        self.assertEqual(still_packed.quantity, 1)

        # check intermediate objects no leftover intermediate packs
        after_split = self.single_result(
            packs_query.filter(
                Goods.state == 'past',
                Goods.reason == unp))
        self.assertEqual(after_split.quantity, 4)
        self.assertEqual(
            packs_query.filter(Goods.state == 'future').count(), 0)

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
            properties=dict(flexible=dict(foo=7)))

        unp = self.Unpack.create(quantity=4,
                                 state='planned',
                                 dt_execution=self.dt_test2,
                                 goods=self.packs)
        self.assertEqual(unp.follows[0].type, 'wms_split')
        self.assertEqual(unp.partial, True)

        unp.cancel()
        Goods = self.Goods
        self.assertEqual(
            Goods.query().filter(Goods.type == unpacked_type).count(),
            0)
        self.assertEqual(
            self.stock.quantity(self.packed_goods_type,
                                goods_state='future',
                                at_datetime=self.dt_test2),
            5)

    def test_no_outcomes(self):
        """Unpacking with no outcomes should be hard errors."""
        self.create_packs(
            type_behaviours=dict(unpack=dict(outcomes=[])),
        )
        self.packs.update(state='present')
        with self.assertRaises(OperationGoodsError) as arc:
            self.Unpack.create(quantity=5,
                               state='done',
                               dt_execution=self.dt_test2,
                               goods=self.packs)
        str(arc.exception)
        repr(arc.exception)
        self.assertEqual(arc.exception.kwargs,
                         dict(type=self.packed_goods_type,
                              packs=self.packs,
                              behaviour=dict(outcomes=[]),
                              specific=()))

    def test_no_behaviour(self):
        """Unpacking with no specified 'unpack' behaviour is an error."""
        self.create_packs(
            type_behaviours=dict(other_op=[]),
        )
        self.packs.update(state='present')
        with self.assertRaises(OperationGoodsError) as arc:
            self.Unpack.create(quantity=5,
                               state='done',
                               dt_execution=self.dt_test2,
                               goods=self.packs)
        str(arc.exception)
        repr(arc.exception)
        self.assertEqual(arc.exception.kwargs,
                         dict(type=self.packed_goods_type,
                              goods=self.packs))

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
        unp = self.Unpack.create(quantity=5, state='planned', goods=self.packs,
                                 dt_execution=self.dt_test2)
        repr(unp)
        str(unp)
