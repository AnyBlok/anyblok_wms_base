# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
import itertools
from datetime import datetime

from anyblok_wms_base.testing import BlokTestCase
from anyblok_wms_base.testing import WmsTestCase
from anyblok_wms_base.constants import CONTENTS_PROPERTY
from anyblok_wms_base.exceptions import (
    OperationError,
    OperationInputsError,
    AssemblyInputNotMatched,
    AssemblyWrongInputProperties,
    AssemblyPropertyConflict,
    UnknownExpressionType,
)


class TestAssembly(WmsTestCase):

    def setUp(self):
        super(TestAssembly, self).setUp()
        self.Assembly = self.Operation.Assembly
        self.Avatar = self.PhysObj.Avatar

        self.stock = self.insert_location('STOCK')

    def create_outcome_type(self, behaviour):
        self.outcome_type = self.PhysObj.Type.insert(
            code='assout',
            behaviours=dict(assembly=behaviour))

    def create_goods(self, spec, state='present', location=None):
        """Create PhysObj and their avatars.

        :param spec: iterable of pairs (PhysObj Type, quantity)
        :return: list of Avatars following the same order as in ``spec``
        """
        Arrival = self.Operation.Arrival
        arrival_state = 'planned' if state == 'future' else 'done'
        created = []
        if location is None:
            location = self.stock
        for gt, qty in spec:
            for _ in range(qty):
                arrival = Arrival.create(physobj_type=gt,
                                         location=location,
                                         state=arrival_state,
                                         dt_execution=self.dt_test1)
                created.append(arrival.outcomes[0])
        return created

    def test_create_done_fixed(self):
        gt1 = self.PhysObj.Type.insert(code='GT1')
        gt2 = self.PhysObj.Type.insert(code='GT2')
        self.create_outcome_type(dict(default={
            'inputs': [
                {'type': 'GT1', 'quantity': 2},
                {'type': 'GT2', 'quantity': 1},
            ],
            'for_contents': ['all', 'descriptions'],
        }))
        avatars = self.create_goods(((gt1, 2), (gt2, 1)))
        avatars[0].obj.set_property('expiration_date', '2010-01-01')

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='default',
                                        state='done')

        outcome = self.assert_singleton(assembly.outcomes)
        self.assertEqual(outcome.obj.type, self.outcome_type)
        self.assertEqual(outcome.state, 'present')
        for av in avatars:
            self.assertEqual(av.state, 'past')
        self.assertEqual(outcome.obj.get_property(CONTENTS_PROPERTY),
                         [dict(properties=dict(batch=None,
                                               expiration_date='2010-01-01'),
                               type='GT1',
                               quantity=1),
                          dict(type='GT1',
                               quantity=1),
                          dict(type='GT2',
                               quantity=1),
                          ])

    def test_create_done_fixed_generic_type(self):
        parent = self.PhysObj.Type.insert(code='parent')
        gt1 = self.PhysObj.Type.insert(code='GT1', parent=parent,
                                       properties=dict(colour='blue', foo=3))
        gt2 = self.PhysObj.Type.insert(code='GT2', parent=parent,
                                       properties=dict(colour='red', foo=4))
        self.create_outcome_type(dict(default={
            'inputs': [
                {'type': 'parent',
                 'quantity': 1,
                 'properties': {
                     'planned': {
                         'required_values': {'main': True},
                     },
                     'started': {
                         'forward': ['colour', 'bar'],
                     },
                 }},
                {'type': 'parent',
                 'quantity': 1,
                 'properties': {
                     'planned': {
                         'required_values': {'colour': 'red'},
                         'forward': ['foo'],
                     },
                 }}
            ],
            'for_contents': ['all', 'descriptions'],
        }))
        avatars = self.create_goods(((gt1, 1), (gt2, 1)))
        avatars[0].obj.set_property('main', True)
        avatars[0].obj.set_property('bar', 1)

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='default',
                                        state='done')

        outcome = self.assert_singleton(assembly.outcomes)
        self.assertEqual(outcome.obj.type, self.outcome_type)
        self.assertEqual(outcome.state, 'present')
        for av in avatars:
            self.assertEqual(av.state, 'past')
        self.assertEqual(outcome.obj.get_property(CONTENTS_PROPERTY),
                         [dict(forward_properties=['bar'],
                               properties=dict(batch=None, main=True),
                               type='GT1',
                               quantity=1),
                          dict(type='GT2',
                               quantity=1),
                          ])
        self.assertEqual(outcome.obj.get_property('colour'), 'blue')
        self.assertEqual(outcome.obj.get_property('foo'), 4)
        self.assertEqual(outcome.obj.get_property('bar'), 1)

    def test_create_done_required_props_match(self):
        """required_properties should be a matching rule, not an aftercheck.

        The specification takes two inputs with the same type, with different
        required_properties rules, and we will forward the 'bar' property
        only from the input that has the 'foo' property, and 'baz' only from
        the one that hasn't.

        Then we'll create two PhysObj, one with 'foo' the other without it and
        fetch them to Assemblies in the two possible orderings (in real
        applicative code, since it comes from the DB, the ordering has
        to be considered random).
        """
        gt1 = self.PhysObj.Type.insert(code='GT1')

        self.create_outcome_type(dict(default={
            'inputs': [
                {'type': 'GT1',
                 'quantity': 1,
                 'properties': {
                     'planned': {
                         'required': ['foo'],
                         'forward': ['bar'],
                     },
                 }},
                {'type': 'GT1',
                 'quantity': 1,
                 'properties': {
                     'planned': {
                         'required': ['foo2'],
                         'forward': ['bar2'],
                     },
                 }},
            ],
        }))
        avatars = self.create_goods(((gt1, 1), (gt1, 1)))
        avatars[0].obj.set_property('foo', 3)
        avatars[0].obj.set_property('bar', 5)
        avatars[0].obj.set_property('bar2', 6)
        avatars[1].obj.set_property('foo2', 4)
        avatars[1].obj.set_property('bar', 2)
        avatars[1].obj.set_property('bar2', 7)

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
            self.assertEqual(outcome.obj.get_property('bar'), 5)
            self.assertEqual(outcome.obj.get_property('bar2'), 7)

            # for next run in the loop
            assembly.obliviate()

    def test_create_done_required_props_match_with_values(self):
        gt1 = self.PhysObj.Type.insert(code='GT1')

        self.create_outcome_type(dict(default={
            'inputs': [
                {'type': 'GT1',
                 'quantity': 1,
                 'properties': {
                     'planned': {
                         'required_values': {'foo': 1},
                         'forward': ['bar'],
                      }},
                 },
                {'type': 'GT1',
                 'quantity': 1,
                 'properties': {
                     'planned': {
                         'required_values': {'foo': 2},
                         'forward': ['bar2'],
                      }},
                 },
            ],
        }))
        avatars = self.create_goods(((gt1, 1), (gt1, 1)))
        avatars[0].obj.set_property('foo', 1)
        avatars[0].obj.set_property('bar', 5)
        avatars[0].obj.set_property('bar2', 6)
        avatars[1].obj.set_property('foo', 2)
        avatars[1].obj.set_property('bar', 2)
        avatars[1].obj.set_property('bar2', 7)

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
            self.assertEqual(outcome.obj.get_property('bar'), 5)
            self.assertEqual(outcome.obj.get_property('bar2'), 7)

            # for next run in the loop
            assembly.obliviate()

    def test_create_done_fwd_contents(self):
        """Forwarding contents should be possible."""
        gt1 = self.PhysObj.Type.insert(code='GT1')
        self.create_outcome_type(dict(default={
            'inputs': [
                {'type': 'GT1', 'quantity': 1},
            ],
            'inputs_properties': {
                'done': {
                    'forward': [CONTENTS_PROPERTY],
                },
            },
        }))
        avatars = self.create_goods([(gt1, 1)])

        self.PhysObj.Type.insert(code='GT2')
        avatars[0].obj.set_property(CONTENTS_PROPERTY,
                                    dict(type='GT2', quantity=4))

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='default',
                                        state='done')

        outcome = self.assert_singleton(assembly.outcomes)
        self.assertEqual(outcome.obj.get_property(CONTENTS_PROPERTY),
                         dict(type='GT2', quantity=4))

    def test_create_done_forward_props_per_inputs_spec_revert(self):
        gt1 = self.PhysObj.Type.insert(code='GT1')
        gt2 = self.PhysObj.Type.insert(code='GT2')
        self.create_outcome_type(dict(default={
            'inputs': [
                {'type': 'GT1', 'quantity': 2,
                 'properties': {
                     'done': {
                         'required_values': {'qa': 'ok'},
                         'requirements': 'match',
                         'forward': ['foo'],
                     },
                  },
                 },
                {'type': 'GT2', 'quantity': 1,
                 'properties': {
                     'planned': {
                         'forward': ['foo', 'bar'],
                     }
                 }},
            ],
            'for_contents': ['all', 'descriptions'],
        }))
        self.outcome_type.behaviours['unpack'] = {}
        avatars = self.create_goods(((gt1, 2), (gt2, 1)))
        for av in avatars:
            av.obj.set_property('foo', 2018)
        avatars[1].obj.set_property('foo', 2018)
        avatars[0].obj.set_property('qa', 'ok')
        avatars[1].obj.set_property('qa', 'ok')
        avatars[2].obj.set_property('bar', 17)

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='default',
                                        state='done')

        pack = self.assert_singleton(assembly.outcomes)
        self.assertEqual(
            pack.obj.properties.as_dict(),
            dict(foo=2018,
                 bar=17,
                 # The 'batch' property is there in all our tests,
                 # because it's a field property installed by a test blok
                 # hence it always is at least None.
                 batch=None,
                 contents=[dict(properties=dict(batch=None, qa='ok'),
                                type='GT1',
                                forward_properties=['foo'],
                                quantity=1),
                           dict(properties=dict(batch=None, qa='ok'),
                                type='GT1',
                                forward_properties=['foo'],
                                quantity=1),
                           dict(properties=dict(batch=None),
                                type='GT2',
                                forward_properties=['bar', 'foo'],
                                quantity=1),
                           ]))

        self.assertEqual(len(assembly.match), 2)
        self.assertEqual(set(assembly.match[0]),
                         set(av.id for av in avatars[:2]))
        self.assertEqual(assembly.match[1], [avatars[2].id])

        # before reversal, it's possible that the pack Properties have
        # changed. That is legitimate
        pack.obj.set_property('bar', 18)
        reversal = assembly.plan_revert()[0]
        reversal.execute()

        for av in avatars:
            self.assertEqual(av.state, 'past')
        self.assertTrue(pack.state, 'past')
        new_avatars = reversal.outcomes
        # since we used the 'description' option in for_outcomes,
        # we also have new PhysObj records
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
        gt1 = self.PhysObj.Type.insert(code='GT1')
        gt2 = self.PhysObj.Type.insert(code='GT2')
        self.create_outcome_type(dict(default={
            'inputs': [
                {'type': 'GT1', 'quantity': 2,
                 'properties': {
                     'done': {
                         'required_values': {'qa': 'ok'},
                         'requirements': 'match',
                         'forward': ['foo'],
                     },
                  },
                 },
                {'type': 'GT2', 'quantity': 1,
                 'properties': {
                     'planned': {
                         'forward': ['foo', 'bar'],
                     }
                 }},
            ],
            'for_contents': ['all', 'records'],
        }))
        self.outcome_type.behaviours['unpack'] = {}
        avatars = self.create_goods(((gt1, 2), (gt2, 1)))
        for av in avatars:
            av.obj.set_property('foo', 2018)
        avatars[1].obj.set_property('foo', 2018)
        avatars[0].obj.set_property('qa', 'ok')
        avatars[1].obj.set_property('qa', 'ok')
        avatars[2].obj.set_property('bar', 17)

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='default',
                                        state='done')

        pack = self.assert_singleton(assembly.outcomes)

        # before reversal, it's possible that the pack Properties have
        # changed. That is legitimate
        pack.obj.set_property('bar', 18)

        reversal = assembly.plan_revert()[0]
        reversal.execute()

        for av in avatars:
            self.assertEqual(av.state, 'past')
        self.assertTrue(pack.state, 'past')
        new_avatars = reversal.outcomes
        self.assertEqual(len(new_avatars), 3)
        for av in new_avatars:
            self.assertEqual(av.state, 'present')

        # since we used the 'all' option in for_contents,
        # the new Avatars are for the existing PhysObj records
        self.assertEqual(set(av.obj for av in new_avatars),
                         set(av.obj for av in avatars))
        self.assertEqual(
            list(sorted(self.sorted_props(av) for av in new_avatars)),
            [
                (('bar', 18), ('batch', None), ('foo', 2018)),
                (('batch', None), ('foo', 2018), ('qa', 'ok')),
                (('batch', None), ('foo', 2018), ('qa', 'ok')),
            ])

    def test_create_done_forward_props_global_spec(self):
        gt1 = self.PhysObj.Type.insert(code='GT1')
        gt2 = self.PhysObj.Type.insert(code='GT2')
        self.create_outcome_type(dict(screwing={
            'outcome_properties': {
                'planned': {'bar': ('const', 3)},
                'done': {'done': ('const', True)},
            },
            'inputs_properties': {
                'started': {
                    'required_values': {'qa': 'ok'},
                },
                'done': {
                    'forward': ['foo'],
                },
            },
            'inputs': [
                {'type': 'GT1', 'quantity': 1},
                {'type': 'GT2', 'quantity': 2},
            ],
            'for_contents': ['all', 'descriptions'],
        }))
        avatars = self.create_goods(((gt1, 1), (gt2, 2)))
        common_props = self.PhysObj.Properties.create(foo=12, qa='ok')
        for av in avatars[:2]:
            av.obj.properties = common_props
        avatars[2].obj.set_property('qa', 'ok')

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='screwing',
                                        state='done')

        outprops = self.assert_singleton(assembly.outcomes).obj.properties
        self.assertEqual(
            outprops.as_dict(),
            dict(foo=12,
                 # The 'batch' property is there in all our tests,
                 # because it's a field property installed by a test blok
                 # hence it always is at least None.
                 batch=None,
                 done=True,
                 bar=3,
                 contents=[dict(properties=dict(batch=None, qa='ok'),
                                type='GT1',
                                forward_properties=['foo'],
                                quantity=1),
                           dict(properties=dict(batch=None, qa='ok'),
                                type='GT2',
                                forward_properties=['foo'],
                                quantity=1),
                           dict(properties=dict(batch=None, qa='ok'),
                                type='GT2',
                                quantity=1),
                           ]))

    def test_create_done_forward_props_hook(self):
        """Test hook for properties

        This also demonstrates how to set the minimum of differing values
        from input properties.
        """
        gt1 = self.PhysObj.Type.insert(code='GT1')
        gt2 = self.PhysObj.Type.insert(code='GT2')

        def hook(op, assembled, state, for_creation=False):
            # demonstrates that this is indeed called last
            self.assertEqual(assembled.get('bar'), 3)
            self.assertEqual(assembled.get('done'), True)
            self.assertEqual(assembled.get('foo'), 12)  # forwarded
            # demonstrates that we know the precise matching of inputs
            self.assertEqual(len(op.match), 2)
            self.assertEqual(len(op.match[0]), 1)
            self.assertEqual(len(op.match[1]), 2)
            # op would be called 'self' if the method would be
            # defined by normal subclassing
            return [('by_hook', min(inp.obj.get_property('expiry')
                                    for inp in op.inputs))]
        self.Assembly.outcome_properties_pack = hook

        self.create_outcome_type(dict(pack={
            'outcome_properties': {
                'planned': {'bar': ('const', 3)},
                'done': {'done': ('const', True)},
            },
            'inputs_properties': {
                'done': {
                    'forward': ['foo'],
                    'required_values': {'qa': 'ok'},
                },
            },
            'inputs': [
                {'type': 'GT1', 'quantity': 1},
                {'type': 'GT2', 'quantity': 2},
            ],
            'for_contents': ['all', 'descriptions'],
        }))
        avatars = self.create_goods(((gt1, 1), (gt2, 2)))
        common_props = self.PhysObj.Properties.create(foo=12, qa='ok')
        for av in avatars[:2]:
            av.obj.properties = common_props
        for i, av in enumerate(avatars):
            av.obj.set_property('expiry', 2015 + i)
            av.obj.set_property('qa', 'ok')

        try:
            assembly = self.Assembly.create(inputs=avatars,
                                            outcome_type=self.outcome_type,
                                            name='pack',
                                            state='done')
        finally:
            del self.Assembly.outcome_properties_pack

        outprops = self.assert_singleton(assembly.outcomes).obj.properties
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
                 contents=[dict(properties=dict(batch=None,
                                                qa='ok',
                                                expiry=2015),
                                type='GT1',
                                forward_properties=['foo'],
                                quantity=1),
                           dict(properties=dict(batch=None,
                                                qa='ok',
                                                expiry=2016),
                                type='GT2',
                                forward_properties=['foo'],
                                quantity=1),
                           dict(properties=dict(batch=None,
                                                qa='ok',
                                                expiry=2017),
                                type='GT2',
                                quantity=1),
                           ]))

    def test_create_planned_execute_fixed(self):
        gt1 = self.PhysObj.Type.insert(code='GT1')
        gt2 = self.PhysObj.Type.insert(code='GT2')
        self.create_outcome_type(dict(default={
            'outcome_properties': {
                'planned': {'foo': ('const', 'bar')},
                'done': {'at_exec': ('const', 'it is done')},
            },
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
        self.assertEqual(outcome.obj.type, self.outcome_type)
        self.assertEqual(outcome.state, 'future')
        props = outcome.obj.properties
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
        gt1 = self.PhysObj.Type.insert(code='GT1')
        gt2 = self.PhysObj.Type.insert(code='GT2')
        self.create_outcome_type(dict(pack={
            'outcome_properties': {
                'planned': {'bar': ('const', 'bar')},
                'done': {'at_exec': ('const', 'it is done')},
            },
            'inputs': [
                {'type': 'GT1', 'quantity': 2},
                {'type': 'GT2', 'quantity': 1},
            ]
        }))

        def hook(op, assembled, state, for_creation=False):
            return [(
                'by_hook',
                'at %s (for_creation=%r)' % (state, for_creation))]

        self.Assembly.outcome_properties_pack = hook

        avatars = self.create_goods(((gt1, 2), (gt2, 1)))

        try:
            assembly = self.Assembly.create(inputs=avatars,
                                            outcome_type=self.outcome_type,
                                            name='pack',
                                            dt_execution=self.dt_test2,
                                            state='planned')
            outcome = self.assert_singleton(assembly.outcomes)
            props = outcome.obj.properties
            self.assertEqual(props.get('by_hook'),
                             'at planned (for_creation=True)')

            assembly.execute()
        finally:
            del self.Assembly.outcome_properties_pack

        self.assertEqual(props.get('by_hook'), 'at done (for_creation=False)')

    def test_create_planned_inputs_spec_fwd(self):
        gt1 = self.PhysObj.Type.insert(code='GT1')
        gt2 = self.PhysObj.Type.insert(code='GT2')
        self.create_outcome_type(dict(default={
            'inputs': [
                {'type': 'GT1', 'quantity': 1,
                 'properties': {'planned': {'forward': ['foo']},
                                'done': {'forward': ['foo', 'bar']}}
                 },
                {'type': 'GT2', 'quantity': 1},
            ]
        }))
        avatars = self.create_goods(((gt1, 1), (gt2, 1)))
        avatars[0].obj.set_property('foo', 23)

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='default',
                                        dt_execution=self.dt_test2,
                                        state='planned')

        outcome = self.assert_singleton(assembly.outcomes)
        self.assertEqual(outcome.obj.type, self.outcome_type)
        self.assertEqual(outcome.state, 'future')
        props = outcome.obj.properties
        self.assertEqual(props.get('foo'), 23)
        self.assertFalse('bar' in props)

        for av in avatars:
            self.assertEqual(av.state, 'present')

        # foo's value changes before execution (imagine there's
        # an Observation happening in between)
        avatars[0].obj.update_properties(dict(foo=-1, bar='ok'))

        assembly.execute()
        self.assertEqual(outcome.state, 'present')
        for av in avatars:
            self.assertEqual(av.state, 'past')

        self.assertEqual(props.get('foo'), -1)
        self.assertEqual(props.get('bar'), 'ok')

    def test_create_done_extra_forbidden(self):
        gt1 = self.PhysObj.Type.insert(code='GT1')
        gt2 = self.PhysObj.Type.insert(code='GT2')
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
        gt1 = self.PhysObj.Type.insert(code='GT1')
        gt2 = self.PhysObj.Type.insert(code='GT2')

        self.create_outcome_type(dict(default={
            'inputs_properties': {
                'planned': {
                    'forward': ['foo'],
                },
            },
            'inputs': [{'type': 'GT1', 'quantity': 2}],
            'allow_extra_inputs': True,
        }))
        avatars = self.create_goods(((gt1, 2), (gt2, 1)))
        avatars[-1].obj.set_property('foo', 17)

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='default',
                                        state='done')

        outcome = self.assert_singleton(assembly.outcomes)
        self.assertEqual(outcome.obj.type, self.outcome_type)
        # property has been forwarded from the extra
        self.assertEqual(outcome.obj.get_property('foo'), 17)
        self.assertEqual(outcome.state, 'present')
        self.assertEqual(outcome.obj.get_property(CONTENTS_PROPERTY),
                         [dict(type='GT2',
                               forward_properties=['foo'],
                               properties=dict(batch=None),
                               quantity=1,
                               local_physobj_ids=[avatars[-1].obj.id])])
        self.assertEqual(len(assembly.match), 1)
        self.assertEqual(set(assembly.match[0]),
                         set(av.id for av in avatars[:2]))

    def test_create_done_extra_no_contents_prop(self):
        gt1 = self.PhysObj.Type.insert(code='GT1')
        gt2 = self.PhysObj.Type.insert(code='GT2')

        self.create_outcome_type(dict(default={
            'inputs': [{'type': 'GT1', 'quantity': 2}],
            'allow_extra_inputs': True,
            'for_contents': None,
        }))
        avatars = self.create_goods(((gt1, 2), (gt2, 1)))

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='default',
                                        state='done')

        outcome = self.assert_singleton(assembly.outcomes)
        self.assertEqual(outcome.obj.type, self.outcome_type)
        self.assertEqual(outcome.state, 'present')
        self.assertIsNone(outcome.obj.get_property(CONTENTS_PROPERTY))

    def test_create_done_extra_parameters(self):
        gt1 = self.PhysObj.Type.insert(code='GT1')

        self.create_outcome_type(dict(default={
            'inputs': [
                {'type': 'GT1',
                 'quantity': 1,
                 'properties': {
                     'planned': {
                         'forward': ['foo1']
                     }}
                 },
                {'type': 'GT1',
                 'quantity': 1,
                 'properties': {
                     'planned': {
                         'forward': ['foo2']
                     }}
                 },
                {'type': 'GT1',
                 'quantity': 1,
                 'properties': {
                     'planned': {
                         'forward': ['foo3']
                     }}
                 },
            ],
        }))
        avatars = self.create_goods(((gt1, 3), ))
        for i, av in enumerate(avatars):
            for foo in range(1, 4):
                av.obj.set_property('foo%d' % foo, 'av%d' % i)
        avatars[0].obj.code = 'HOP'

        av1_id = avatars[1].obj.id
        extra_params = dict(inputs=[dict(id=av1_id),
                                    dict(code='HOP'),
                                    {},
                                    ])

        for inputs in itertools.permutations(avatars):
            assembly = self.Assembly.create(inputs=avatars,
                                            outcome_type=self.outcome_type,
                                            name='default',
                                            parameters=extra_params,
                                            dt_execution=self.dt_test1,
                                            state='planned')
            self.assertEqual(
                assembly.specification['inputs'],
                [{'type': 'GT1',
                  'quantity': 1,
                  'id': av1_id,
                  'properties': {
                      'planned': {
                          'forward': ['foo1']
                      }}
                  },
                 {'type': 'GT1',
                  'quantity': 1,
                  'code': 'HOP',
                  'properties': {
                      'planned': {
                          'forward': ['foo2']
                      }}
                  },
                 {'type': 'GT1',
                  'quantity': 1,
                  'properties': {
                      'planned': {
                          'forward': ['foo3']
                      }}
                  },
                 ])

            outcome_goods = self.assert_singleton(assembly.outcomes).obj

            self.assertEqual(outcome_goods.get_property('foo1'), 'av1')
            self.assertEqual(outcome_goods.get_property('foo2'), 'av0')
            self.assertEqual(outcome_goods.get_property('foo3'), 'av2')
            assembly.cancel()

    def test_create_basic_errors(self):
        gt = self.PhysObj.Type.insert(code='GT1')

        avatars = self.create_goods(((gt, 2), ))

        # with no assembly behaviour
        no_assembly = self.PhysObj.Type.insert(code='noass',
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
        other_loc = self.PhysObj.insert(code='other',
                                        type=self.stock.type)
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

    def test_unmatched_required_properties(self):
        gt1 = self.PhysObj.Type.insert(code='GT1')

        self.create_outcome_type(dict(default={
            'inputs': [
                # note how the most precise is first, this is what
                # applications are expected to do, since the criteria
                # are evaluated in order
                {'type': 'GT1',
                 'quantity': 1,
                 'properties': {
                     'started': {
                         'required_values': {'qa': 'ok'},
                     },
                  },
                 },
                {'type': 'GT1',
                 'quantity': 1,
                 'properties': {
                     'started': {
                         'required': ['qa'],
                     },
                  },
                 },
            ],
        }))
        avatars = self.create_goods(((gt1, 1), (gt1, 1)))
        avatars[0].obj.set_property('qa', 'ok')

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
                              properties=dict(
                                  started=dict(
                                      required=['qa'],
                                  )))
                         )
        self.assertEqual(exc.kwargs['from_state'], None)
        self.assertEqual(exc.kwargs['to_state'], 'done')

    def test_unmatched_required_property_value(self):
        gt1 = self.PhysObj.Type.insert(code='GT1')

        self.create_outcome_type(dict(default={
            'inputs': [
                {'type': 'GT1',
                 'quantity': 1,
                 'properties': {
                     'started': {
                         'required_values': {'qa': 'ok'},
                         },
                     },
                 },
            ],
        }))
        avatars = self.create_goods(((gt1, 1), ))
        avatars[0].obj.set_property('qa', 'broken')

        with self.assertRaises(AssemblyInputNotMatched) as arc:
            self.Assembly.create(inputs=avatars,
                                 outcome_type=self.outcome_type,
                                 name='default',
                                 state='done')
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['spec_nr'], 1)
        self.assertEqual(exc.kwargs['spec_index'], 0)
        self.assertEqual(exc.kwargs['spec_detail'],
                         dict(type='GT1',
                              quantity=1,
                              properties=dict(
                                  started=dict(
                                      required_values=dict(qa='ok')
                                  )))
                         )
        self.assertEqual(exc.kwargs['from_state'], None)
        self.assertEqual(exc.kwargs['to_state'], 'done')

    def test_unmatched_global_required_property_value(self):
        gt1 = self.PhysObj.Type.insert(code='GT1')

        self.create_outcome_type(dict(default={
            'inputs_properties': {
                'started': {
                    'required_values': {'qa': 'ok'},
                },
            },
            'inputs': [
                {'type': 'GT1',
                 'quantity': 1,
                 },
            ],
        }))
        avatars = self.create_goods(((gt1, 1), ))
        avatars[0].obj.set_property('qa', 'broken')

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='default',
                                        dt_execution=self.dt_test1,
                                        state='planned')
        with self.assertRaises(AssemblyWrongInputProperties) as arc:
            assembly.execute()

        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['required_props'], set())
        self.assertEqual(exc.kwargs['required_prop_values'], dict(qa='ok'))
        self.assertEqual(exc.kwargs['avatar'], avatars[0])

    def test_unmatched_per_input_required_property_value(self):
        gt1 = self.PhysObj.Type.insert(code='GT1')

        self.create_outcome_type(dict(default={
            'inputs_properties': {
            },
            'inputs': [
                {'type': 'GT1',
                 'quantity': 1,
                 'properties': {
                     'started': {
                         'required_values': {'qa': 'ok'},
                     },
                  },
                 },
            ],
        }))
        avatars = self.create_goods(((gt1, 1), ))
        avatars[0].obj.set_property('qa', 'broken')

        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='default',
                                        dt_execution=self.dt_test1,
                                        state='planned')
        with self.assertRaises(AssemblyWrongInputProperties) as arc:
            assembly.execute()

        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['required_props'], set())
        self.assertEqual(exc.kwargs['required_prop_values'], dict(qa='ok'))
        self.assertEqual(exc.kwargs['avatar'], avatars[0])
        self.assertEqual(exc.kwargs['spec_idx'], 0)
        self.assertEqual(exc.kwargs['spec_nr'], 1)
        self.assertEqual(exc.kwargs['spec_detail'],
                         dict(type='GT1',
                              quantity=1,
                              properties=dict(
                                  started=dict(
                                      required_values=dict(qa='ok')))))

    def test_unmatched_code(self):
        gt1 = self.PhysObj.Type.insert(code='GT1')

        self.create_outcome_type(dict(default={
            'inputs': [
                {'type': 'GT1',
                 'quantity': 1,
                 'code': 'brian',
                 },
            ],
        }))
        avatars = self.create_goods(((gt1, 1), ))
        goods = avatars[0].obj

        with self.assertRaises(AssemblyInputNotMatched) as arc:
            self.Assembly.create(inputs=avatars,
                                 outcome_type=self.outcome_type,
                                 name='default',
                                 dt_execution=self.dt_test1,
                                 state='planned')
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['spec_nr'], 1)
        self.assertEqual(exc.kwargs['spec_index'], 0)
        self.assertEqual(exc.kwargs['spec_detail'],
                         dict(type='GT1',
                              quantity=1,
                              code='brian'))

        goods.code = 'brian'
        # now it works
        assembly = self.Assembly.create(inputs=avatars,
                                        outcome_type=self.outcome_type,
                                        name='default',
                                        dt_execution=self.dt_test1,
                                        state='planned')
        assembly.cancel()

        # now requiring an unmatchable id (0)
        with self.assertRaises(AssemblyInputNotMatched) as arc:
            self.Assembly.create(inputs=avatars,
                                 outcome_type=self.outcome_type,
                                 parameters=dict(inputs=[dict(id=0)]),
                                 dt_execution=self.dt_test1,
                                 name='default',
                                 state='planned')
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['spec_nr'], 1)
        self.assertEqual(exc.kwargs['spec_index'], 0)
        self.assertEqual(exc.kwargs['spec_detail'],
                         dict(type='GT1',
                              quantity=1,
                              id=0,
                              code='brian'))

    def test_inconsistent_forwarding_one_spec(self):
        gt1 = self.PhysObj.Type.insert(code='GT1')

        self.create_outcome_type(dict(default=dict(
            inputs=[dict(type='GT1', quantity=2,
                         properties=dict(done=dict(forward=['bar'])))],
            )))
        avatars = self.create_goods([(gt1, 2)])
        avatars[0].obj.set_property('bar', 1)
        avatars[1].obj.set_property('bar', 2)

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
                              properties=dict(done=dict(forward=['bar']))))

    def test_inconsistent_forwarding_extra(self):
        gt1 = self.PhysObj.Type.insert(code='GT1')

        # This exception raising happens only for extra inputs
        # as the requirements on the matching ones (global or per input spec)
        # are tested in one shot, always raising with the input spec details
        self.create_outcome_type(dict(default=dict(
            inputs_properties=dict(
                planned=dict(forward=['bar'])
            ),
            inputs=[],
            allow_extra_inputs=True,
            )))
        avatars = self.create_goods([(gt1, 2)])
        avatars[0].obj.set_property('bar', 1)
        avatars[1].obj.set_property('bar', 2)

        with self.assertRaises(AssemblyPropertyConflict) as arc:
            self.Assembly.create(inputs=avatars,
                                 outcome_type=self.outcome_type,
                                 name='default',
                                 state='done')
        exc = arc.exception
        str(exc)
        repr(exc)
        self.assertEqual(exc.kwargs['prop'], 'bar')
        self.assertEqual(set((exc.kwargs['existing'],
                              exc.kwargs['candidate'])), {1, 2})
        self.assertEqual(exc.kwargs['global_extra'], True)

    def test_inconsistent_forwarding_two_specs(self):
        """Error raised by conflicting props due to different input specs.

        This also demonstrates that the input specs are treated into order,
        therefore "existing" and "candidate" are deterministic.
        """
        gt1 = self.PhysObj.Type.insert(code='GT1')
        gt2 = self.PhysObj.Type.insert(code='GT2')

        self.create_outcome_type(dict(default=dict(
            inputs=[dict(type='GT1', quantity=1,
                         properties=dict(done=dict(forward=['bar']))),
                    dict(type='GT2', quantity=1,
                         properties=dict(done=dict(forward=['bar']))),
                    ]
            )))
        avatars = self.create_goods([(gt1, 1), (gt2, 1)])
        avatars[0].obj.set_property('bar', 1)
        avatars[1].obj.set_property('bar', 2)

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
                              properties=dict(done=dict(forward=['bar']))))

    def test_merged_state_parameter(self):
        # well ok, we'll put it later in a separate utility module
        # but that requires thinking of a naming that'd be clear out of
        # the Assembly context
        from anyblok_wms_base.core.operation.assembly import (
            merge_state_parameter)

        # unknown type
        with self.assertRaises(ValueError):
            merge_state_parameter({}, None, 'done', 'int')

        # normalization in case spec is None
        self.assertEqual(
            merge_state_parameter(None, 'planned', 'done', 'set'),
            set())
        self.assertEqual(
            merge_state_parameter(None, 'planned', 'done', 'dict'),
            {})

        spec = dict(planned=dict(x=1),
                    started=dict(y=2),
                    done=dict(z=3))
        self.assertEqual(
            merge_state_parameter(spec, None, 'done', 'dict'),
            dict(x=1, y=2, z=3))
        self.assertEqual(
            merge_state_parameter(spec, 'planned', 'done', 'dict'),
            dict(y=2, z=3))
        self.assertEqual(
            merge_state_parameter(spec, 'started', 'done', 'dict'),
            dict(z=3))
        self.assertEqual(
            merge_state_parameter(spec, None, 'started', 'dict'),
            dict(x=1, y=2))
        self.assertEqual(
            merge_state_parameter(spec, 'planned', 'started', 'dict'),
            dict(y=2))
        self.assertEqual(
            merge_state_parameter(spec, None, 'planned', 'dict'),
            dict(x=1))

        # using CheckMatch

        spec = dict(planned='check',
                    started='match',
                    done='check')
        self.assertFalse(
            merge_state_parameter(
                spec, None, 'planned',
                'check_match').is_match)
        self.assertTrue(
            merge_state_parameter(
                spec, None, 'started',
                'check_match').is_match)
        self.assertTrue(
            merge_state_parameter(
                spec, None, 'done',
                'check_match').is_match)

        # CheckMatch with gaps
        # not that the wished default 'check' value for 'planned'
        # is not this function's responsibility, but its caller's
        spec = dict(started='match')
        self.assertFalse(
            merge_state_parameter(
                spec, None, 'planned',
                'check_match').is_match)
        self.assertTrue(
            merge_state_parameter(
                spec, None, 'started',
                'check_match').is_match)
        self.assertTrue(
            merge_state_parameter(
                spec, None, 'done',
                'check_match').is_match)
        self.assertTrue(
            merge_state_parameter(
                spec, 'planned', 'done',
                'check_match').is_match)
        self.assertFalse(
            merge_state_parameter(
                spec, 'started', 'done',
                'check_match').is_match)

    def test_merged_state_sub_parameters(self):
        # well ok, we'll put it later in a separate utility module
        # but that requires thinking of a naming that'd be clear out of
        # the Assembly context
        from anyblok_wms_base.core.operation.assembly import (
            merge_state_sub_parameters)

        # unknown type
        with self.assertRaises(ValueError):
            merge_state_sub_parameters({}, None, 'done', ('foo', 'int'))

        # normalization in case spec is None
        self.assertEqual(merge_state_sub_parameters(None, 'planned', 'done',
                                                    ('foo', 'set'),
                                                    ('bar', 'dict')),
                         [set(), {}])

        # simple display of the state jumps
        spec = dict(planned=dict(x=['a']),
                    started=dict(x=['b']),
                    done=dict(x=['c']))
        self.assertEqual(
            merge_state_sub_parameters(
                spec, None, 'done', ('x', 'set')),
            {'a', 'b', 'c'})
        self.assertEqual(
            merge_state_sub_parameters(
                spec, 'planned', 'done', ('x', 'set')),
            {'b', 'c'})
        self.assertEqual(
            merge_state_sub_parameters(
                spec, 'started', 'done', ('x', 'set')),
            {'c'})

        self.assertEqual(
            merge_state_sub_parameters(
                spec, None, 'started', ('x', 'set')),
            {'a', 'b'})
        self.assertEqual(
            merge_state_sub_parameters(
                spec, 'planned', 'started', ('x', 'set')),
            {'b'})

        self.assertEqual(
            merge_state_sub_parameters(
                spec, None, 'planned', ('x', 'set')),
            {'a'})

    def test_CheckMatch(self):
        from anyblok_wms_base.core.operation.assembly import CheckMatch

        c = CheckMatch()
        self.assertFalse(c.is_match)

        c.update('check')
        self.assertFalse(c.is_match)

        with self.assertRaises(ValueError) as arc:
            c.update('foo')
        self.assertEqual(arc.exception.args, ('foo', ))

        c.update('match')
        self.assertTrue(c.is_match)

        c.update('check')
        self.assertTrue(c.is_match)


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
            outcome_type=Wms.PhysObj.Type.insert(code='whatever'),
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
