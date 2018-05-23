# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from datetime import datetime

from anyblok_wms_base.testing import BlokTestCase
from anyblok_wms_base.testing import WmsTestCase
from anyblok_wms_base.exceptions import (
    OperationError,
    OperationInputsError,
    AssemblyInputNotMatched,
    AssemblyPropertyConflict,
    UnknownExpressionType,
)


class TestAssembly(WmsTestCase):

    def setUp(self):
        super(TestAssembly, self).setUp()
        Wms = self.registry.Wms
        self.Operation = Operation = Wms.Operation
        self.Assembly = Operation.Assembly
        self.Goods = Wms.Goods
        self.Avatar = Wms.Goods.Avatar

        self.stock = Wms.Location.insert(label="Stock")

    def create_outcome_type(self, behaviour):
        self.outcome_type = self.Goods.Type.insert(
            code='assout',
            behaviours=dict(assembly=behaviour))

    def create_goods(self, spec, state='present', location=None):
        """Create Goods and their avatars.

        :param spec: iterable of pairs (Goods Type, quantity)
        :return: list of Avatars following the same order as in ``spec``
        """
        Arrival = self.Operation.Arrival
        arrival_state = 'planned' if state == 'future' else 'done'
        created = []
        if location is None:
            location = self.stock
        for gt, qty in spec:
            for _ in range(qty):
                arrival = Arrival.create(goods_type=gt,
                                         location=location,
                                         state=arrival_state,
                                         dt_execution=self.dt_test1)
                created.append(arrival.outcomes[0])
        return created

    def test_create_done_fixed(self):
        gt1 = self.Goods.Type.insert(code='GT1')
        gt2 = self.Goods.Type.insert(code='GT2')
        self.create_outcome_type(dict(default={
            'inputs': [
                {'type': 'GT1', 'quantity': 2},
                {'type': 'GT2', 'quantity': 1},
            ],
            'for_unpack_outcomes': ['all', 'descriptions'],
        }))
        avatars = self.create_goods(((gt1, 2), (gt2, 1)))
        avatars[0].goods.set_property('expiration_date', '2010-01-01')

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='default',
                                        state='done')

        outcome = self.assert_singleton(assembly.outcomes)
        self.assertEqual(outcome.goods.type, self.outcome_type)
        self.assertEqual(outcome.state, 'present')
        for av in avatars:
            self.assertEqual(av.state, 'past')
        self.assertEqual(outcome.goods.get_property('unpack_outcomes'),
                         [dict(properties=dict(batch=None,
                                               expiration_date='2010-01-01'),
                               type=gt1.id,
                               quantity=1),
                          dict(type=gt1.id,
                               quantity=1),
                          dict(type=gt2.id,
                               quantity=1),
                          ])

    def test_create_done_fixed_generic_type(self):
        parent = self.Goods.Type.insert(code='parent')
        gt1 = self.Goods.Type.insert(code='GT1', parent=parent,
                                     properties=dict(colour='blue', foo=3))
        gt2 = self.Goods.Type.insert(code='GT2', parent=parent,
                                     properties=dict(colour='red', foo=4))
        self.create_outcome_type(dict(default={
            'inputs': [
                {'type': 'parent',
                 'quantity': 1,
                 'required_property_values': {'main': True},
                 'forward_properties': ['colour', 'bar'],
                 },
                {'type': 'parent',
                 'quantity': 1,
                 'required_property_values': {'colour': 'red'},
                 'forward_properties': ['foo'],
                 }
            ],
            'for_unpack_outcomes': ['all', 'descriptions'],
        }))
        avatars = self.create_goods(((gt1, 1), (gt2, 1)))
        avatars[0].goods.set_property('main', True)
        avatars[0].goods.set_property('bar', 1)

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='default',
                                        state='done')

        outcome = self.assert_singleton(assembly.outcomes)
        self.assertEqual(outcome.goods.type, self.outcome_type)
        self.assertEqual(outcome.state, 'present')
        for av in avatars:
            self.assertEqual(av.state, 'past')
        self.assertEqual(outcome.goods.get_property('unpack_outcomes'),
                         [dict(forward_properties=['bar'],
                               properties=dict(batch=None, main=True),
                               type=gt1.id,
                               quantity=1),
                          dict(type=gt2.id,
                               quantity=1),
                          ])
        self.assertEqual(outcome.goods.get_property('colour'), 'blue')
        self.assertEqual(outcome.goods.get_property('foo'), 4)
        self.assertEqual(outcome.goods.get_property('bar'), 1)

    def test_create_done_required_props_match(self):
        """required_properties should be a matching rule, not an aftercheck.

        The specification takes two inputs with the same type, with different
        required_properties rules, and we will forward the 'bar' property
        only from the input that has the 'foo' property, and 'baz' only from
        the one that hasn't.

        Then we'll create two Goods, one with 'foo' the other without it and
        fetch them to Assemblies in the two possible orderings (in real
        applicative code, since it comes from the DB, the ordering has
        to be considered random).
        """
        gt1 = self.Goods.Type.insert(code='GT1')

        self.create_outcome_type(dict(default={
            'inputs': [
                {'type': 'GT1',
                 'quantity': 1,
                 'required_properties': ['foo'],
                 'forward_properties': ['bar'],
                 },
                {'type': 'GT1',
                 'quantity': 1,
                 'required_properties': ['foo2'],
                 'forward_properties': ['bar2'],
                 },
            ],
        }))
        avatars = self.create_goods(((gt1, 1), (gt1, 1)))
        avatars[0].goods.set_property('foo', 3)
        avatars[0].goods.set_property('bar', 5)
        avatars[0].goods.set_property('bar2', 6)
        avatars[1].goods.set_property('foo2', 4)
        avatars[1].goods.set_property('bar', 2)
        avatars[1].goods.set_property('bar2', 7)

        # if the ordering in implementation is a function of the orderings
        # inputs, then any selection based on type followed by a later check
        # on props will fail at least one of these, namely the one that selects
        # avatars[1] first.
        for inputs in (avatars, list(reversed(avatars))):

            assembly = self.Assembly.create(inputs=inputs,
                                            outcome_type=self.outcome_type,
                                            name='default',
                                            state='done')

            outcome = self.assert_singleton(assembly.outcomes)
            self.assertEqual(outcome.goods.get_property('bar'), 5)
            self.assertEqual(outcome.goods.get_property('bar2'), 7)

            # for next run in the loop
            assembly.obliviate()

    def test_create_done_required_props_match_with_values(self):
        gt1 = self.Goods.Type.insert(code='GT1')

        self.create_outcome_type(dict(default={
            'inputs': [
                {'type': 'GT1',
                 'quantity': 1,
                 'required_property_values': dict(foo=1),
                 'forward_properties': ['bar'],
                 },
                {'type': 'GT1',
                 'quantity': 1,
                 'required_properties': dict(foo=2),
                 'forward_properties': ['bar2'],
                 },
            ],
        }))
        avatars = self.create_goods(((gt1, 1), (gt1, 1)))
        avatars[0].goods.set_property('foo', 1)
        avatars[0].goods.set_property('bar', 5)
        avatars[0].goods.set_property('bar2', 6)
        avatars[1].goods.set_property('foo', 2)
        avatars[1].goods.set_property('bar', 2)
        avatars[1].goods.set_property('bar2', 7)

        # if the ordering in implementation is a function of the orderings
        # inputs, then any selection based on type followed by a later check
        # on props will fail at least one of these, namely the one that selects
        # avatars[1] first.
        for inputs in (avatars, list(reversed(avatars))):

            assembly = self.Assembly.create(inputs=inputs,
                                            outcome_type=self.outcome_type,
                                            name='default',
                                            state='done')

            outcome = self.assert_singleton(assembly.outcomes)
            self.assertEqual(outcome.goods.get_property('bar'), 5)
            self.assertEqual(outcome.goods.get_property('bar2'), 7)

            # for next run in the loop
            assembly.obliviate()

    def test_create_done_fwd_unpack_outcomes(self):
        """Forwarding unpack_outcomes should be possible."""
        gt1 = self.Goods.Type.insert(code='GT1')
        self.create_outcome_type(dict(default={
            'inputs': [
                {'type': 'GT1', 'quantity': 1},
            ],
            'forward_properties': ['unpack_outcomes'],
        }))
        avatars = self.create_goods([(gt1, 1)])

        gt2 = self.Goods.Type.insert(code='GT2')
        avatars[0].goods.set_property('unpack_outcomes',
                                      dict(type=gt2.id, quantity=4))

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='default',
                                        state='done')

        outcome = self.assert_singleton(assembly.outcomes)
        self.assertEqual(outcome.goods.get_property('unpack_outcomes'),
                         dict(type=gt2.id, quantity=4))

    def test_create_done_forward_props_per_inputs_spec_revert(self):
        gt1 = self.Goods.Type.insert(code='GT1')
        gt2 = self.Goods.Type.insert(code='GT2')
        self.create_outcome_type(dict(default={
            'inputs': [
                {'type': 'GT1', 'quantity': 2,
                 'forward_properties': ['foo'],
                 'required_property_values': {'qa': 'ok'},
                 },
                {'type': 'GT2', 'quantity': 1,
                 'forward_properties': ['foo', 'bar'],
                 },
            ],
            'for_unpack_outcomes': ['all', 'descriptions'],
        }))
        self.outcome_type.behaviours['unpack'] = {}
        avatars = self.create_goods(((gt1, 2), (gt2, 1)))
        for av in avatars:
            av.goods.set_property('foo', 2018)
        avatars[1].goods.set_property('foo', 2018)
        avatars[0].goods.set_property('qa', 'ok')
        avatars[1].goods.set_property('qa', 'ok')
        avatars[2].goods.set_property('bar', 17)

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='default',
                                        state='done')

        pack = self.assert_singleton(assembly.outcomes)
        self.assertEqual(
            pack.goods.properties.as_dict(),
            dict(foo=2018,
                 bar=17,
                 # The 'batch' property is there in all our tests,
                 # because it's a field property installed by a test blok
                 # hence it always is at least None.
                 batch=None,
                 unpack_outcomes=[dict(properties=dict(batch=None, qa='ok'),
                                       type=gt1.id,
                                       forward_properties=['foo'],
                                       quantity=1),
                                  dict(properties=dict(batch=None, qa='ok'),
                                       type=gt1.id,
                                       forward_properties=['foo'],
                                       quantity=1),
                                  dict(properties=dict(batch=None),
                                       type=gt2.id,
                                       forward_properties=['bar', 'foo'],
                                       quantity=1),
                                  ]))

        # before reversal, it's possible that the pack Properties have
        # changed. That is legitimate
        pack.goods.set_property('bar', 18)
        reversal = assembly.plan_revert()[0]
        reversal.execute()

        for av in avatars:
            self.assertEqual(av.state, 'past')
        self.assertTrue(pack.state, 'past')
        new_avatars = reversal.outcomes
        # since we used the 'description' option in for_outcomes,
        # we also have new Goods records
        self.assertEqual(len(new_avatars), 3)
        for av in new_avatars:
            self.assertEqual(av.state, 'present')

        self.assertEqual(
            list(sorted(self.sorted_props(av) for av in new_avatars)),
            [
                (('bar', 18), ('batch', None), ('foo', 2018)),
                (('batch', None), ('foo', 2018), ('qa', 'ok')),
                (('batch', None), ('foo', 2018), ('qa', 'ok')),
            ])

    def test_create_done_forward_props_revert_same_goods(self):
        gt1 = self.Goods.Type.insert(code='GT1')
        gt2 = self.Goods.Type.insert(code='GT2')
        self.create_outcome_type(dict(default={
            'inputs': [
                {'type': 'GT1', 'quantity': 2,
                 'forward_properties': ['foo'],
                 'required_property_values': {'qa': 'ok'},
                 },
                {'type': 'GT2', 'quantity': 1,
                 'forward_properties': ['foo', 'bar'],
                 },
            ],
            'for_unpack_outcomes': ['all', 'records'],
        }))
        self.outcome_type.behaviours['unpack'] = {}
        avatars = self.create_goods(((gt1, 2), (gt2, 1)))
        for av in avatars:
            av.goods.set_property('foo', 2018)
        avatars[1].goods.set_property('foo', 2018)
        avatars[0].goods.set_property('qa', 'ok')
        avatars[1].goods.set_property('qa', 'ok')
        avatars[2].goods.set_property('bar', 17)

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='default',
                                        state='done')

        pack = self.assert_singleton(assembly.outcomes)

        # before reversal, it's possible that the pack Properties have
        # changed. That is legitimate
        pack.goods.set_property('bar', 18)

        reversal = assembly.plan_revert()[0]
        reversal.execute()

        for av in avatars:
            self.assertEqual(av.state, 'past')
        self.assertTrue(pack.state, 'past')
        new_avatars = reversal.outcomes
        self.assertEqual(len(new_avatars), 3)
        for av in new_avatars:
            self.assertEqual(av.state, 'present')

        # since we used the 'all' option in for_unpack_outcomes,
        # the new Avatars are for the existing Goods records
        self.assertEqual(set(av.goods for av in new_avatars),
                         set(av.goods for av in avatars))
        self.assertEqual(
            list(sorted(self.sorted_props(av) for av in new_avatars)),
            [
                (('bar', 18), ('batch', None), ('foo', 2018)),
                (('batch', None), ('foo', 2018), ('qa', 'ok')),
                (('batch', None), ('foo', 2018), ('qa', 'ok')),
            ])

    def test_create_done_forward_props_global_spec(self):
        gt1 = self.Goods.Type.insert(code='GT1')
        gt2 = self.Goods.Type.insert(code='GT2')
        self.create_outcome_type(dict(screwing={
            'properties': {'bar': ('const', 3)},
            'properties_at_execution': {'done': ('const', True)},
            'forward_properties': ['foo'],
            'required_property_values': {'qa': 'ok'},
            'inputs': [
                {'type': 'GT1', 'quantity': 1},
                {'type': 'GT2', 'quantity': 2},
            ],
            'for_unpack_outcomes': ['all', 'descriptions'],
        }))
        avatars = self.create_goods(((gt1, 1), (gt2, 2)))
        common_props = self.Goods.Properties.create(foo=12, qa='ok')
        for av in avatars[:2]:
            av.goods.properties = common_props
        avatars[2].goods.set_property('qa', 'ok')

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='screwing',
                                        state='done')

        outprops = self.assert_singleton(assembly.outcomes).goods.properties
        self.assertEqual(
            outprops.as_dict(),
            dict(foo=12,
                 # The 'batch' property is there in all our tests,
                 # because it's a field property installed by a test blok
                 # hence it always is at least None.
                 batch=None,
                 done=True,
                 bar=3,
                 unpack_outcomes=[dict(properties=dict(batch=None, qa='ok'),
                                       type=gt1.id,
                                       forward_properties=['foo'],
                                       quantity=1),
                                  dict(properties=dict(batch=None, qa='ok'),
                                       type=gt2.id,
                                       forward_properties=['foo'],
                                       quantity=1),
                                  dict(properties=dict(batch=None, qa='ok'),
                                       type=gt2.id,
                                       quantity=1),
                                  ]))

    def test_create_done_forward_props_hook(self):
        """Test hook for properties

        This also demonstrates how to set the minimum of differing values
        from input properties.
        """
        gt1 = self.Goods.Type.insert(code='GT1')
        gt2 = self.Goods.Type.insert(code='GT2')

        def hook(op, assembled, for_exec=False):
            # demonstrates that this is indeed called last
            self.assertEqual(assembled.get('bar'), 3)
            self.assertEqual(assembled.get('done'), True)
            self.assertEqual(assembled.get('foo'), 12)  # forwarded
            # op would be called 'self' if the method would be
            # defined by normal subclassing
            return [('by_hook', min(inp.goods.get_property('expiry')
                                    for inp in op.inputs))]
        self.Assembly.build_outcome_properties_pack = hook

        self.create_outcome_type(dict(pack={
            'properties': {'bar': ('const', 3)},
            'properties_at_execution': {'done': ('const', True)},
            'forward_properties': ['foo'],
            'required_property_values': {'qa': 'ok'},
            'inputs': [
                {'type': 'GT1', 'quantity': 1},
                {'type': 'GT2', 'quantity': 2},
            ],
            'for_unpack_outcomes': ['all', 'descriptions'],
        }))
        avatars = self.create_goods(((gt1, 1), (gt2, 2)))
        common_props = self.Goods.Properties.create(foo=12, qa='ok')
        for av in avatars[:2]:
            av.goods.properties = common_props
        for i, av in enumerate(avatars):
            av.goods.set_property('expiry', 2015 + i)
            av.goods.set_property('qa', 'ok')

        try:
            assembly = self.Assembly.create(inputs=avatars,
                                            outcome_type=self.outcome_type,
                                            name='pack',
                                            state='done')
        finally:
            del self.Assembly.build_outcome_properties_pack

        outprops = self.assert_singleton(assembly.outcomes).goods.properties
        self.assertEqual(
            outprops.as_dict(),
            dict(foo=12,
                 # The 'batch' property is there in all our tests,
                 # because it's a field property installed by a test blok
                 # hence it always is at least None.
                 batch=None,
                 done=True,
                 bar=3,
                 by_hook=2015,
                 unpack_outcomes=[dict(properties=dict(batch=None,
                                                       qa='ok',
                                                       expiry=2015),
                                       type=gt1.id,
                                       forward_properties=['foo'],
                                       quantity=1),
                                  dict(properties=dict(batch=None,
                                                       qa='ok',
                                                       expiry=2016),
                                       type=gt2.id,
                                       forward_properties=['foo'],
                                       quantity=1),
                                  dict(properties=dict(batch=None,
                                                       qa='ok',
                                                       expiry=2017),
                                       type=gt2.id,
                                       quantity=1),
                                  ]))

    def test_create_planned_execute_fixed(self):
        gt1 = self.Goods.Type.insert(code='GT1')
        gt2 = self.Goods.Type.insert(code='GT2')
        self.create_outcome_type(dict(default={
            'properties': {'foo': ['const', 'bar']},
            'properties_at_execution': {'at_exec': ['const', 'it is done']},
            'inputs': [
                {'type': 'GT1', 'quantity': 2},
                {'type': 'GT2', 'quantity': 1},
            ]
        }))
        avatars = self.create_goods(((gt1, 2), (gt2, 1)))

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='default',
                                        dt_execution=self.dt_test2,
                                        state='planned')

        outcome = self.assert_singleton(assembly.outcomes)
        self.assertEqual(outcome.goods.type, self.outcome_type)
        self.assertEqual(outcome.state, 'future')
        props = outcome.goods.properties
        self.assertEqual(props.get('foo'), 'bar')
        self.assertFalse('at_exec' in props)

        for av in avatars:
            self.assertEqual(av.state, 'present')

        assembly.execute()
        self.assertEqual(outcome.state, 'present')
        for av in avatars:
            self.assertEqual(av.state, 'past')

        self.assertEqual(props.get('foo'), 'bar')
        self.assertEqual(props.get('at_exec'), "it is done")

    def test_create_planned_execute_fixed_hook(self):
        gt1 = self.Goods.Type.insert(code='GT1')
        gt2 = self.Goods.Type.insert(code='GT2')
        self.create_outcome_type(dict(pack={
            'properties': {'foo': ['const', 'bar']},
            'properties_at_execution': {'at_exec': ['const', 'it is done']},
            'inputs': [
                {'type': 'GT1', 'quantity': 2},
                {'type': 'GT2', 'quantity': 1},
            ]
        }))

        def hook(op, assembled, for_exec=False):
            return [(
                'by_hook',
                'at ' + ('execution' if for_exec else 'planification'))]

        self.Assembly.build_outcome_properties_pack = hook

        avatars = self.create_goods(((gt1, 2), (gt2, 1)))

        try:
            assembly = self.Assembly.create(inputs=avatars,
                                            outcome_type=self.outcome_type,
                                            name='pack',
                                            dt_execution=self.dt_test2,
                                            state='planned')
            outcome = self.assert_singleton(assembly.outcomes)
            props = outcome.goods.properties
            self.assertEqual(props.get('by_hook'), 'at planification')

            assembly.execute()
        finally:
            del self.Assembly.build_outcome_properties_pack

        self.assertEqual(props.get('by_hook'), 'at execution')

    def test_create_done_extra_forbidden(self):
        gt1 = self.Goods.Type.insert(code='GT1')
        gt2 = self.Goods.Type.insert(code='GT2')
        self.create_outcome_type(dict(default={
            'inputs': [{'type': 'GT1', 'quantity': 2}],
        }))
        self.create_outcome_type(dict(default={
            'inputs': [{'type': 'GT1', 'quantity': 2}],
        }))

        avatars = self.create_goods(((gt1, 2), (gt2, 1)))

        with self.assertRaises(OperationInputsError) as arc:
            self.Assembly.create(inputs=avatars,
                                 outcome_type=self.outcome_type,
                                 name='default',
                                 state='done')

        exc = arc.exception
        str(exc)
        repr(exc)

    def test_create_done_extra_allowed(self):
        gt1 = self.Goods.Type.insert(code='GT1')
        gt2 = self.Goods.Type.insert(code='GT2')
        self.create_outcome_type(dict(default={
            'inputs': [{'type': 'GT1', 'quantity': 2}],
            'allow_extra_inputs': True,
        }))
        self.create_outcome_type(
            dict(default=dict(
                inputs=[dict(type='GT1', quantity=2)],
                allow_extra_inputs=True)))
        avatars = self.create_goods(((gt1, 2), (gt2, 1)))

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='default',
                                        state='done')

        outcome = self.assert_singleton(assembly.outcomes)
        self.assertEqual(outcome.goods.type, self.outcome_type)
        self.assertEqual(outcome.state, 'present')
        self.assertEqual(outcome.goods.get_property('unpack_outcomes'),
                         [dict(type=gt2.id,
                               quantity=1,
                               local_goods_ids=[avatars[-1].goods.id])])

    def test_create_basic_errors(self):
        gt = self.Goods.Type.insert(code='GT1')

        avatars = self.create_goods(((gt, 2), ))

        # with no assembly behaviour
        no_assembly = self.Goods.Type.insert(code='noass',
                                             behaviours=dict(foo='bar'))
        with self.assertRaises(OperationError) as arc:
            self.Assembly.create(inputs=avatars,
                                 outcome_type=no_assembly,
                                 name='default',
                                 state='done')
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['outcome_type'], no_assembly)

        # with ill-named assembly behaviour
        self.create_outcome_type(
            dict(hop=dict(
                inputs=[dict(type='GT1', quantity=2)]
                )))

        with self.assertRaises(OperationError) as arc:
            self.Assembly.create(inputs=avatars,
                                 outcome_type=self.outcome_type,
                                 name='wrong',
                                 state='done')
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['outcome_type'], self.outcome_type)
        self.assertEqual(exc.kwargs['name'], 'wrong')

        # several locations in inputs
        other_loc = self.registry.Wms.Location.insert(code='other')
        avatars[0].location = other_loc
        with self.assertRaises(OperationError) as arc:
            self.Assembly.create(inputs=avatars,
                                 outcome_type=self.outcome_type,
                                 name='hop',
                                 state='done')
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs.get('locations'),
                         {self.stock, other_loc})

    def test_unmatched_input_spec(self):
        gt1 = self.Goods.Type.insert(code='GT1')

        self.create_outcome_type(dict(default={
            'inputs': [
                # note how the most precise is first, this is what
                # applications are expected to do, since the criteria
                # are evaluated in order
                {'type': 'GT1',
                 'quantity': 1,
                 'required_property_values': {'qa': 'ok'},
                 },
                {'type': 'GT1',
                 'quantity': 1,
                 'required_properties': ['qa'],
                 },
            ],
        }))
        avatars = self.create_goods(((gt1, 1), (gt1, 1)))
        avatars[0].goods.set_property('qa', 'ok')

        with self.assertRaises(AssemblyInputNotMatched) as arc:
            self.Assembly.create(inputs=avatars,
                                 outcome_type=self.outcome_type,
                                 name='default',
                                 state='done')
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['spec_nr'], 2)
        self.assertEqual(exc.kwargs['spec_index'], 1)
        self.assertEqual(exc.kwargs['spec_detail'],
                         dict(type='GT1',
                              quantity=1,
                              required_properties=['qa']))

    def test_inconsistent_forwarding_one_spec(self):
        gt1 = self.Goods.Type.insert(code='GT1')

        self.create_outcome_type(dict(default=dict(
            inputs=[dict(type='GT1', quantity=2, forward_properties=['bar'])],
            )))
        avatars = self.create_goods([(gt1, 2)])
        avatars[0].goods.set_property('bar', 1)
        avatars[1].goods.set_property('bar', 2)

        with self.assertRaises(AssemblyPropertyConflict) as arc:
            self.Assembly.create(inputs=avatars,
                                 outcome_type=self.outcome_type,
                                 name='default',
                                 state='done')
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['spec_nr'], 1)
        self.assertEqual(exc.kwargs['spec_index'], 0)
        self.assertEqual(exc.kwargs['prop'], 'bar')
        self.assertEqual(set((exc.kwargs['existing'],
                              exc.kwargs['candidate'])), {1, 2})
        self.assertEqual(exc.kwargs['spec_detail'],
                         dict(type='GT1',
                              quantity=2,
                              forward_properties=['bar']))

    def test_inconsistent_forwarding_two_specs(self):
        """Error raised by conflicting props due to different input specs.

        This also demonstrates that the input specs are treated into order,
        therefore "existing" and "candidate" are deterministic.
        """
        gt1 = self.Goods.Type.insert(code='GT1')
        gt2 = self.Goods.Type.insert(code='GT2')

        self.create_outcome_type(dict(default=dict(
            inputs=[dict(type='GT1', quantity=1, forward_properties=['bar']),
                    dict(type='GT2', quantity=1, forward_properties=['bar'])],
            )))
        avatars = self.create_goods([(gt1, 1), (gt2, 1)])
        avatars[0].goods.set_property('bar', 1)
        avatars[1].goods.set_property('bar', 2)

        with self.assertRaises(AssemblyPropertyConflict) as arc:
            self.Assembly.create(inputs=avatars,
                                 outcome_type=self.outcome_type,
                                 name='default',
                                 state='done')
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['spec_nr'], 2)
        self.assertEqual(exc.kwargs['spec_index'], 1)
        self.assertEqual(exc.kwargs['prop'], 'bar')
        self.assertEqual(exc.kwargs['existing'], 1)
        self.assertEqual(exc.kwargs['candidate'], 2)
        self.assertEqual(exc.kwargs['spec_detail'],
                         dict(type='GT2',
                              quantity=1,
                              forward_properties=['bar']))


class TestTypedExpression(BlokTestCase):
    """Separate class for typed expression testing.

    The typed expression feature will probably in the future be provided
    by a global module or a Mixin.
    """

    def setUp(self):
        # this test needs an Operation with eval_typed_expr(),
        # whose details don't matter.
        Wms = self.registry.Wms
        self.operation = Wms.Operation.Assembly.insert(
            outcome_type=Wms.Goods.Type.insert(code='whatever'),
            dt_execution=datetime.now(),
            state='planned')
        self.eval_typed_expr = self.operation.eval_typed_expr

    def test_const(self):
        self.assertEqual(self.eval_typed_expr('const', 'hop'), 'hop')
        self.assertEqual(self.eval_typed_expr('const', 12), 12)

    def test_seq(self):
        self.registry.System.Sequence.insert(code='prd',
                                             number=12,
                                             formater='PRD/{seq}')
        self.assertEqual(self.eval_typed_expr('sequence', 'prd'), 'PRD/12')
        self.assertEqual(self.eval_typed_expr('sequence', 'prd'), 'PRD/13')

    def test_unknown_expression(self):
        with self.assertRaises(UnknownExpressionType) as arc:
            self.eval_typed_expr('c0nst', 'bar')
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['expr_type'], 'c0nst')
        self.assertEqual(exc.kwargs['expr_value'], 'bar')
