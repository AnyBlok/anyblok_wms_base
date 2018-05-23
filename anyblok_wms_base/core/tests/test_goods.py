# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCase
from anyblok.tests.testcase import BlokTestCase


class TestGoods(WmsTestCase):

    blok_entry_points = ('bloks', 'test_bloks')

    def setUp(self):
        super(TestGoods, self).setUp()
        Wms = self.registry.Wms

        self.Goods = Wms.Goods
        self.Avatar = Wms.Goods.Avatar
        self.goods_type = self.Goods.Type.insert(label="My goods", code="MG")
        self.stock = Wms.Location.insert(label="Stock")
        self.arrival = Wms.Operation.Arrival.insert(
            goods_type=self.goods_type,
            location=self.stock,
            dt_execution=self.dt_test1,
            state='done')

    def test_has_type(self):
        parent = self.Goods.Type.insert(code='parent')
        goods = self.Goods.insert(type=self.goods_type)

        self.assertTrue(goods.has_type(self.goods_type))
        self.assertFalse(goods.has_type(parent))

        self.goods_type.parent = parent
        self.assertTrue(goods.has_type(parent))

    def test_prop_api(self):
        goods = self.Goods.insert(type=self.goods_type)
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
        goods = self.Goods.insert(type=gt)
        avatar = self.Avatar.insert(goods=goods,
                                    dt_from=self.dt_test1,
                                    state='future',
                                    reason=self.arrival, location=self.stock)
        self.assertEqual(repr(goods),
                         "Wms.Goods(id=%d, type="
                         "Wms.Goods.Type(id=%d, code='MG'))" % (
                             goods.id, gt.id))
        self.assertEqual(str(goods),
                         "(id=%d, type="
                         "(id=%d, code='MG'))" % (goods.id, gt.id))
        self.maxDiff = None
        self.assertEqual(
            repr(avatar),
            "Wms.Goods.Avatar(id=%d, "
            "goods=Wms.Goods(id=%d, type=Wms.Goods.Type(id=%d, code='MG')), "
            "state='future', "
            "location=Wms.Location(id=%d, code=None, label='Stock'), "
            "dt_range=[datetime.datetime(2018, 1, 1, 0, 0, "
            "tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)), "
            "None)" % (
                avatar.id, goods.id, gt.id, self.stock.id))

        self.assertEqual(
            str(avatar),
            "(id=%d, "
            "goods=(id=%d, type=(id=%d, code='MG')), "
            "state='future', "
            "location=(id=%d, code=None, label='Stock'), "
            "dt_range=[2018-01-01 00:00:00+00:00, None)" % (
                avatar.id, goods.id, gt.id, self.stock.id))

    def test_prop_api_column(self):
        goods = self.Goods.insert(type=self.goods_type)
        goods.set_property('batch', '12345')
        self.assertEqual(goods.get_property('batch'), '12345')

    def test_prop_api_duplication(self):
        goods = self.Goods.insert(type=self.goods_type)

        goods.set_property('batch', '12345')
        self.assertEqual(goods.get_property('batch'), '12345')

        goods2 = self.Goods.insert(type=self.goods_type,
                                   properties=goods.properties)
        goods2.set_property('batch', '6789')
        self.assertEqual(goods.get_property('batch'), '12345')
        self.assertEqual(goods2.get_property('batch'), '6789')

    def test_prop_api_duplication_not_needed(self):
        goods = self.Goods.insert(type=self.goods_type)

        goods.set_property('batch', '12345')
        self.assertEqual(goods.get_property('batch'), '12345')

        goods2 = self.Goods.insert(type=self.goods_type,
                                   properties=goods.properties)
        goods2.set_property('batch', '12345')
        self.assertEqual(goods.properties, goods2.properties)

    def test_prop_api_update_duplication(self):
        goods = self.Goods.insert(type=self.goods_type)

        # this tests in particular the case with no Properties to begin
        # with
        goods.update_properties(dict(foo=3, bar='xy'))
        self.assertIsNotNone(goods.properties)
        self.assertEqual(goods.properties.as_dict(),
                         dict(foo=3, batch=None, bar='xy'))

        goods2 = self.Goods.insert(type=self.goods_type,
                                   properties=goods.properties)
        goods2.update_properties(dict(foo=4))
        self.assertNotEqual(goods.properties, goods2.properties)
        self.assertEqual(goods2.get_property('foo'), 4)

    def test_prop_api_update_duplication_not_needed(self):
        goods = self.Goods.insert(type=self.goods_type)
        upd = dict(foo=3, bar='xy')
        goods.update_properties(upd)

        goods2 = self.Goods.insert(type=self.goods_type,
                                   properties=goods.properties)
        goods2.update_properties(upd)
        self.assertEqual(goods.properties, goods2.properties)

    def test_prop_api_reserved_property_names(self):
        goods = self.Goods.insert(type=self.goods_type)

        with self.assertRaises(ValueError):
            goods.set_property('id', 1)
        with self.assertRaises(ValueError):
            goods.set_property('flexible', 'foo')

    def test_prop_api_internal(self):
        """Internal implementation details of Goods dict API.

        Separated to ease maintenance of tests in case it changes in
        the future.
        """
        goods = self.Goods.insert(type=self.goods_type)
        goods.set_property('foo', 2)
        self.assertEqual(goods.properties.flexible, dict(foo=2))

    def test_prop_api_column_internal(self):
        """Internal implementation details of Goods dict API (case of column)

        Separated to ease maintenance of tests in case it changes in
        the future.
        """
        goods = self.Goods.insert(type=self.goods_type)

        goods.set_property('batch', '2')
        self.assertEqual(goods.properties.flexible, {})
        self.assertEqual(goods.properties.batch, '2')


class TestGoodsProperties(BlokTestCase):

    def setUp(self):
        self.Props = self.registry.Wms.Goods.Properties

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
