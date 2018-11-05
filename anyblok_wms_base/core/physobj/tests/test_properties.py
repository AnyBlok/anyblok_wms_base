# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
"""Tests of Wms.PhysObj.Properties.

This is not about tests of Wms.PhysObj involving properties
(for these, see test_goods).
"""

from anyblok.tests.testcase import BlokTestCase


class TestPhysObjProperties(BlokTestCase):
    def setUp(self):
        self.Props = self.registry.Wms.PhysObj.Properties

    def test_get_set(self):
        props = self.Props.insert()

        # at this stage, props.flexible is None, but get() and [] must behave
        # as if it were an empty dict
        with self.assertRaises(KeyError) as arc:
            props['foo']
        self.assertEqual(arc.exception.args, ('foo', ))
        self.assertIsNone(props.get('foo'))
        self.assertEqual(props.get('foo', 4), 4)

        props['foo'] = 3
        props[123] = 'bar'
        props['batch'] = 1

        self.assertEqual(props['foo'], 3)
        self.assertEqual(props.get('foo'), 3)

        self.assertEqual(props[123], 'bar')
        self.assertEqual(props.get(123), 'bar')

        self.assertEqual(props['batch'], 1)
        self.assertEqual(props.get('batch'), 1)

        self.assertIsNone(props.get('missing'))
        self.assertEqual(props.get('missing', 1.2), 1.2)

        with self.assertRaises(TypeError):
            self.assertEqual(props.get('a', 'default', 'extra'))

    def test_update(self):
        props = self.Props()

        with self.assertRaises(TypeError):
            # two positional arguments
            props.update(dict(a=1), dict(b=2))

        # a dict positional arg
        props.update(dict(batch=1))
        # an iterable of pairs
        props.update([('x', 2), ('y', 3)])
        # keyword arguments
        props.update(z=5, foo='bar')

        self.assertEqual(props.as_dict(),
                         dict(batch=1, x=2, y=3, z=5, foo='bar'))

        # both positional and keywords arguments (yes it works with dicts)
        # also, overwritting existing properties
        props.update(dict(batch=3), z=['a', 'b'], foo='spam')
        self.assertEqual(props.as_dict(),
                         dict(batch=3, x=2, y=3, z=['a', 'b'], foo='spam'))

    def test_create(self):
        props = self.Props.create(batch='abcd',
                                  serial=1234, expiry='2018-03-01')
        self.assertEqual(props.to_dict(),
                         dict(batch='abcd',
                              id=props.id,
                              flexible=dict(serial=1234, expiry='2018-03-01')))

        self.assertIsNone(self.Props.create())

    def test_reserved(self):
        with self.assertRaises(ValueError):
            self.Props.create(batch='abcd', flexible=True)

    def test_as_dict(self):
        props = self.Props.create(batch='abcd', history=['a'], serial=2345)
        as_dict = props.as_dict()
        self.assertEqual(as_dict,
                         dict(batch='abcd', history=['a'], serial=2345))

        # mutability issues
        as_dict['history'].append('b')
        self.assertEqual(props.get('history'), ['a'])

    def test_contains(self):
        props = self.Props.insert(batch='abc')
        self.assertTrue('batch' in props)
        self.assertFalse('x' in props)  # props.flexible is None
        props['x'] = 1
        self.assertTrue('x' in props)
        self.assertFalse('y' in props)  # props.flexible isn't None

    def test_duplicate(self):
        props = self.Props.create(batch='abcd', history=['a'], serial=2345)
        dup = props.duplicate()
        self.assertNotEqual(dup.id, props.id)
        self.assertEqual(dup.as_dict(),
                         dict(batch='abcd', history=['a'], serial=2345))

        # niceties with mutability
        dup.get('history').append('b')
        self.assertEqual(dup.get('history'), ['a', 'b'])
        self.assertEqual(props.get('history'), ['a'])

    def test_del_pop(self):
        missing = object()
        props = self.Props(batch='abcd')

        # case where flexible is None
        with self.assertRaises(KeyError):
            del props['history']
        with self.assertRaises(KeyError):
            props.pop('history')
        with self.assertRaises(TypeError):
            props.pop('history', 1, 2)
        self.assertEqual(props.pop('history', ['x']), ['x'])

        props['history'] = ['a', 'b']
        self.assertEqual(props['history'], ['a', 'b'])
        del props['history']

        self.assertFalse('history' in props)
        self.assertEqual(props.get('history', missing), missing)

        for k in ('id', 'flexible', 'batch'):
            with self.assertRaises(ValueError):
                del props[k]

        props['foo'] = 14

        self.assertEqual(props.pop('foo'), 14)
        self.assertEqual(props.pop('foo', missing), missing)
        self.assertFalse('foo' in props)
        self.assertEqual(props.get('foo', missing), missing)

        for k in ('id', 'flexible', 'batch'):
            with self.assertRaises(ValueError):
                props.pop(k)
        with self.assertRaises(TypeError):
            props.pop('foo', 1, 2)

    def test_upgrade_contents_local_goods_ids(self):
        Props = self.Props
        p1_id = Props.insert(flexible=dict(foo='bar')).id
        p2_id = Props.insert(flexible=dict(
            monty='python',
            contents=[
                dict(type='POT1',
                     forward_properties=['foo'],
                     quantity=3,
                     local_goods_ids=[1, 3, 7]),
                dict(type='POT2',
                     forward_properties=['foo'],
                     quantity=3),
            ])).id
        from anyblok.blok import BlokManager
        wms_core = BlokManager.get('wms-core')(self.registry)

        # make sure we have no side effect of Property instances in the
        # session
        self.registry.session.expire_all()

        wms_core.update_contents_property_local_goods_id()

        # and again
        self.registry.flush()
        self.registry.session.expire_all()

        # time for assertions
        p1 = Props.query().get(p1_id)
        self.assertEqual(p1.flexible, dict(foo='bar'))
        p2 = Props.query().get(p2_id)
        self.assertEqual(p2.flexible, dict(
            monty='python',
            contents=[
                dict(type='POT1',
                     forward_properties=['foo'],
                     quantity=3,
                     local_physobj_ids=[1, 3, 7]),
                dict(type='POT2',
                     forward_properties=['foo'],
                     quantity=3)
                ]))
