# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok.tests.testcase import BlokTestCase


class TestGoodsType(BlokTestCase):

    def setUp(self):
        self.Type = self.registry.Wms.Goods.Type

    def test_get_behaviour(self):
        gt = self.Type.insert(code='gtc')
        # there's no 'default_loc' behaviour considered in wms-core
        # at the time being, but that's something applicative code may
        # want to introduce
        self.assertIsNone(gt.get_behaviour('default_loc'))
        self.assertEqual(gt.get_behaviour('default_loc', default='stock'),
                         'stock')
        gt.behaviours = dict(default_loc='AB/1/2')
        self.assertEqual(gt.get_behaviour('default_loc'), 'AB/1/2')
        self.assertIsNone(gt.get_behaviour('other'))
        self.assertEqual(gt.get_behaviour('other', default=1), 1)

    def test_get_behaviour_parent_defaulting(self):
        parent = self.Type.insert(code='gtp')
        child = self.Type.insert(code='gtc', parent=parent)

        parent.behaviours = dict(foo='bar')

        self.assertIsNone(child.behaviours)
        self.assertEqual(child.get_behaviour('foo'), 'bar')

        # with other behaviour on child
        child.behaviours = dict(monty='python')
        self.assertEqual(child.get_behaviour('foo'), 'bar')

        # child shadows parent for non-dict values
        child.behaviours['foo'] = 'spam'
        self.assertEqual(child.get_behaviour('foo'), 'spam')

    def test_get_behaviour_parent_merge(self):
        """Merging a behaviour between a Type and its parent.

        Let's make an useful example: an Asssembly which sets a serial number
        at execution time, using a System.Sequence specified on the parent
        Type (so that all all children of the parent share the same sequence)

        Please note that the assembly itself isn't executed, so that
        this example can get outdated.
        """
        parent = self.Type.insert(
            code='gtp',
            behaviours=dict(
                assembly=dict(
                    screwing=dict(
                        properties_at_execution=dict(
                            serial=('sequence', 'SCRSER')),
                    ))))

        child = self.Type.insert(
            code='gtc1',
            parent=parent,
            behaviours=dict(
                assembly=dict(
                    screwing=dict(
                        inputs=[dict(type='material1', quantity=2)]
                    ))))

        sibling = self.Type.insert(
            code='gtc2',
            parent=parent,
            behaviours=dict(
                assembly=dict(
                    screwing=dict(
                        inputs=[dict(type='material2', quantity=3)]
                    ))))

        self.assertEqual(child.get_behaviour('assembly'),
                         dict(screwing=dict(
                             dict(properties_at_execution=dict(
                                 serial=('sequence', 'SCRSER'))),
                             inputs=[dict(type='material1', quantity=2)],
                         )))

        # no side effect on the parent
        self.assertEqual(parent.behaviours['assembly'],
                         dict(screwing=dict(
                             dict(properties_at_execution=dict(
                                 serial=('sequence', 'SCRSER'))),
                         )))

        # nor on another child
        self.assertEqual(sibling.behaviours['assembly'],
                         dict(screwing=dict(
                             inputs=[dict(type='material2', quantity=3)],
                         )))

    def test_is_subtype(self):
        grand = self.Type.insert(code='grand')
        parent = self.Type.insert(code='parent', parent=grand)
        child = self.Type.insert(code='child', parent=parent)
        sibling = self.Type.insert(code='other', parent=parent)
        stranger = self.Type.insert(code='stranger')

        self.assertTrue(child.is_sub_type(parent))
        self.assertTrue(child.is_sub_type(grand))
        self.assertFalse(parent.is_sub_type(child))
        self.assertFalse(child.is_sub_type(sibling))
        self.assertFalse(child.is_sub_type(stranger))
        self.assertFalse(stranger.is_sub_type(grand))
        self.assertFalse(stranger.is_sub_type(parent))

    def test_query_subtype(self):
        grand = self.Type.insert(code='grand')
        parent = self.Type.insert(code='parent', parent=grand)
        child = self.Type.insert(code='child', parent=parent)
        sibling = self.Type.insert(code='sibling', parent=parent)
        self.Type.insert(code='stranger')

        self.assertEqual(set(self.Type.query_subtypes([parent]).all()),
                         {parent, child, sibling})
        self.assertEqual(set(self.Type.query_subtypes([grand]).all()),
                         {grand, parent, child, sibling})
        aunt = self.Type.insert(code='aunt', parent=grand)
        self.assertEqual(set(self.Type.query_subtypes([grand]).all()),
                         {grand, aunt, parent, child, sibling})

        # direct use as a CTE
        Goods = self.registry.Wms.Goods
        goods = Goods.insert(type=child)
        cte = self.Type.query_subtypes([grand], as_cte=True)
        self.assertEqual(Goods.query()
                         .join(cte, cte.c.id == Goods.type_id).one(),
                         goods)

    def test_properties(self):
        parent = self.Type.insert(code='parent')

        self.assertFalse(parent.has_property('foo'))
        self.assertFalse(parent.has_properties(['foo', 'qa']))
        self.assertTrue(parent.has_properties([]))
        self.assertEqual(parent.merged_properties(), {})
        parent.properties = dict(foo=1, qa='nok')

        self.assertTrue(parent.has_property('foo'))
        self.assertTrue(parent.has_property_values(dict(foo=1)))
        self.assertTrue(parent.has_properties(['foo', 'qa']))
        self.assertFalse(parent.has_property_values(dict(foo=1, qa='ok')))
        self.assertEqual(parent.merged_properties(), dict(foo=1, qa='nok'))

        child = self.Type.insert(code='child', parent=parent)
        self.assertTrue(child.has_property('foo'))
        self.assertTrue(child.has_property_values(dict(foo=1)))
        self.assertTrue(child.has_properties(['foo', 'qa']))
        self.assertFalse(child.has_property_values(dict(foo=1, qa='ok')))
        self.assertEqual(child.merged_properties(), dict(foo=1, qa='nok'))

        child.properties = dict(bar=True)
        self.assertTrue(child.has_property('foo'))
        self.assertTrue(child.has_property_values(dict(foo=1, bar=True)))
        self.assertTrue(child.has_properties(['foo', 'qa', 'bar']))
        self.assertEqual(child.merged_properties(),
                         dict(foo=1, qa='nok', bar=True))

        child.properties['foo'] = 2
        self.assertTrue(child.has_property_values(dict(foo=2, bar=True)))
        self.assertEqual(child.merged_properties(),
                         dict(foo=2, qa='nok', bar=True))
