# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok.tests.testcase import BlokTestCase


class TestPhysObj(BlokTestCase):

    def setUp(self):
        super(TestPhysObj, self).setUp()
        Wms = self.registry.Wms

        self.PhysObj = Wms.PhysObj
        self.goods_type = self.PhysObj.Type.insert(label="My goods",
                                                   code="MG")

    def test_has_type(self):
        parent = self.PhysObj.Type.insert(code='parent')
        goods = self.PhysObj.insert(type=self.goods_type)

        self.assertTrue(goods.has_type(self.goods_type))
        self.assertFalse(goods.has_type(parent))

        self.goods_type.parent = parent
        self.assertTrue(goods.has_type(parent))

    def test_prop_api(self):
        goods = self.PhysObj.insert(type=self.goods_type)
        self.assertIsNone(goods.get_property('foo'))
        self.assertEqual(goods.get_property('foo', default=-1), -1)

        self.assertTrue(goods.has_properties(()))
        self.assertTrue(goods.has_property_values({}))
        self.assertFalse(goods.has_property('foo'))
        self.assertFalse(goods.has_property_values(dict(foo=1)))
        self.assertFalse(goods.has_properties(['foo']))

        goods.set_property('foo', 1)
        self.assertEqual(goods.get_property('foo'), 1)

        self.assertTrue(goods.has_property('foo'))
        self.assertTrue(goods.has_properties(['foo']))

        goods.set_property('bar', 2)
        self.assertTrue(goods.has_properties(['foo', 'bar']))
        self.assertTrue(goods.has_property_values(dict(foo=1, bar=2)))

        goods.update_properties([('foo', 'x'), ('bar', 'y'), ('spam', 'eggs')])
        self.assertEqual(goods.properties.as_dict(),
                         dict(batch=None, foo='x', bar='y', spam='eggs'))
        goods.update_properties(dict(batch=3, spam='no'))
        self.assertEqual(goods.properties.as_dict(),
                         dict(batch=3, foo='x', bar='y', spam='no'))

    def test_str(self):
        gt = self.goods_type
        goods = self.PhysObj.insert(type=gt)
        self.assertEqual(repr(goods),
                         "Wms.PhysObj(id=%d, type="
                         "Wms.PhysObj.Type(id=%d, code='MG'))" % (
                             goods.id, gt.id))
        self.assertEqual(str(goods),
                         "(id=%d, type="
                         "(id=%d, code='MG'))" % (goods.id, gt.id))
        goods.code = 'COCO'
        self.assertEqual(repr(goods),
                         "Wms.PhysObj(id=%d, code='COCO', type=%r)" % (
                             goods.id, gt))
        self.assertEqual(str(goods),
                         "(id=%d, code=COCO, type=%s)" % (
                             goods.id, gt))

    def test_prop_api_column(self):
        goods = self.PhysObj.insert(type=self.goods_type)
        goods.set_property('batch', '12345')
        self.assertEqual(goods.get_property('batch'), '12345')

    def test_prop_api_duplication(self):
        goods = self.PhysObj.insert(type=self.goods_type)

        goods.set_property('batch', '12345')
        self.assertEqual(goods.get_property('batch'), '12345')

        goods2 = self.PhysObj.insert(type=self.goods_type,
                                     properties=goods.properties)
        goods2.set_property('batch', '6789')
        self.assertEqual(goods.get_property('batch'), '12345')
        self.assertEqual(goods2.get_property('batch'), '6789')

    def test_prop_api_duplication_not_needed(self):
        goods = self.PhysObj.insert(type=self.goods_type)

        goods.set_property('batch', '12345')
        self.assertEqual(goods.get_property('batch'), '12345')

        goods2 = self.PhysObj.insert(type=self.goods_type,
                                     properties=goods.properties)
        goods2.set_property('batch', '12345')
        self.assertEqual(goods.properties, goods2.properties)

    def test_prop_api_update_duplication(self):
        goods = self.PhysObj.insert(type=self.goods_type)

        # this tests in particular the case with no Properties to begin
        # with
        goods.update_properties(dict(foo=3, bar='xy'))
        self.assertIsNotNone(goods.properties)
        self.assertEqual(goods.properties.as_dict(),
                         dict(foo=3, batch=None, bar='xy'))

        goods2 = self.PhysObj.insert(type=self.goods_type,
                                     properties=goods.properties)
        goods2.update_properties(dict(foo=4))
        self.assertNotEqual(goods.properties, goods2.properties)
        self.assertEqual(goods2.get_property('foo'), 4)

    def test_prop_api_update_duplication_not_needed(self):
        goods = self.PhysObj.insert(type=self.goods_type)
        upd = dict(foo=3, bar='xy')
        goods.update_properties(upd)

        goods2 = self.PhysObj.insert(type=self.goods_type,
                                     properties=goods.properties)
        goods2.update_properties(upd)
        self.assertEqual(goods.properties, goods2.properties)

    def test_prop_api_reserved_property_names(self):
        goods = self.PhysObj.insert(type=self.goods_type)

        with self.assertRaises(ValueError):
            goods.set_property('id', 1)
        with self.assertRaises(ValueError):
            goods.set_property('flexible', 'foo')

    def test_merged_properties(self):
        parent = self.goods_type
        child = self.PhysObj.Type.insert(code='child', parent=parent)
        goods = self.PhysObj.insert(type=child)
        goods.set_property('holy', 'grail')
        self.assertEqual(goods.merged_properties(),
                         dict(holy='grail',
                              batch=None),  # always present (column)
                         )
        parent.properties = dict(holy='arthur')
        child.properties = dict(bar=2)
        self.assertEqual(goods.merged_properties(),
                         dict(holy='grail',
                              bar=2,
                              batch=None),  # always present (column)
                         )

    def test_merged_properties_type_only(self):
        parent = self.goods_type
        child = self.PhysObj.Type.insert(code='child', parent=parent)

        goods = self.PhysObj.insert(type=child)
        self.assertEqual(goods.merged_properties(), {})

        parent.properties = dict(holy='arthur')
        child.properties = dict(bar=2)
        self.assertEqual(goods.merged_properties(),
                         dict(holy='arthur',
                              bar=2))

    def test_prop_api_internal(self):
        """Internal implementation details of PhysObj dict API.

        Separated to ease maintenance of tests in case it changes in
        the future.
        """
        goods = self.PhysObj.insert(type=self.goods_type)
        goods.set_property('foo', 2)
        self.assertEqual(goods.properties.flexible, dict(foo=2))

    def test_prop_api_column_internal(self):
        """Internal implementation details of PhysObj dict API (case of column)

        Separated to ease maintenance of tests in case it changes in
        the future.
        """
        goods = self.PhysObj.insert(type=self.goods_type)

        goods.set_property('batch', '2')
        self.assertEqual(goods.properties.flexible, {})
        self.assertEqual(goods.properties.batch, '2')
