# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from datetime import datetime
from psycopg2.tz import FixedOffsetTimezone
import sqlalchemy
from sqlalchemy.event import listens_for

import anyblok.registry
from anyblok.config import Configuration
from anyblok.tests.testcase import BlokTestCase

try:
    from anyblok.tests.testcase import SharedDataTestCase
except ImportError:
    from .sdtestcase import SharedDataTestCase

_missing = object()


class WmsTestCase(BlokTestCase):
    """Provide some common utilities.

    Probably some of these should be contributed back into Anyblok, but
    we'll see.
    """

    default_quantity_location = None

    @classmethod
    def setUpClass(cls):
        super(WmsTestCase, cls).setUpClass()
        cls.Wms = Wms = cls.registry.Wms
        cls.Operation = Wms.Operation
        cls.Goods = Wms.Goods

    def setUp(self):
        tz = self.tz = FixedOffsetTimezone(0)
        self.dt_test1 = datetime(2018, 1, 1, tzinfo=tz)
        self.dt_test2 = datetime(2018, 1, 2, tzinfo=tz)
        self.dt_test3 = datetime(2018, 1, 3, tzinfo=tz)

    def single_result(self, query):
        """Assert that query as a single result and return it.

        This is better than one() in that it will issue a Failure instead of
        an error.
        """
        results = query.all()
        self.assertEqual(len(results), 1)
        return results[0]

    def assert_singleton(self, collection):
        """Assert that collection has exactly one element and return the latter.

        This help improving reader's focus, while never throwing an Error

        :param collection:
           whatever is iterable and implements ``len()`.
           These criteria cover at least list, tuple, set, frozenset…

        Note that mapping types typically would return their unique *key*
        """
        self.assertEqual(len(collection), 1)
        for elt in collection:
            return elt

    def assert_quantity(self, quantity, location=_missing, goods_type=_missing,
                        **kwargs):
        if location is _missing:
            location = self.default_quantity_location
        if goods_type is _missing:
            goods_type = self.goods_type

        self.assertEqual(self.Wms.quantity(location=location,
                                           goods_type=goods_type,
                                           **kwargs), quantity)

    def sorted_props(self, record):
        """Extract Goods Properties, as a sorted tuple.

        :param record: either a Wms.Goods or Wms.Goods.Avatar instance
        The tuple is hashable, and sorting it removes randomness
        """
        model = record.__registry_name__
        if model == 'Model.Wms.Goods.Avatar':
            goods = record.goods
        elif model == 'Model.Wms.Goods':
            goods = record
        else:
            self.fail("%r is neither a Goods nor an Avatar instance" % record)
        return tuple(sorted(goods.properties.as_dict().items()))

    @classmethod
    def create_location_type(cls):
        loc_type = cls.location_type = cls.Wms.Goods.Type.insert(code="LOC")
        return loc_type

    def insert_location(self, code, location_type=None, **kwargs):
        """Helper for location creations,

        :param location_type: if not specified, ``self.location_type`` and
                              ``cls.location.type`` are tried, in that order.
                              If the latter doesn't exist, it is created.
        :param parent: if specified, the inserted location gets an Avatar
                       that places it inside the ``parent`` location.
        """
        if location_type is None:
            location_type = getattr(self, 'location_type', None)
        dt_from = getattr(self, 'dt_test1', None)
        return self.cls_insert_location(code,
                                        location_type=location_type,
                                        dt_from=dt_from,
                                        **kwargs)

    @classmethod
    def cls_insert_location(cls, code,
                            location_type=None, parent=None, tag=None,
                            dt_from=None,
                            **fields):
        """Helper for location creations, classmethod version

        :param location_type: if not specified, ``cls.location_type``
                              is created if not already and used.
        :param parent: if specified, the inserted location gets an Avatar
                       that places it inside the ``parent`` location.
        :param dt_from: used if ``parent`` is specified, as the starting date
                        of the corresponding Avatar, with fallback onto
                        ``cls.dt_test1``.
        """
        if location_type is None:
            location_type = getattr(cls, 'location_type', None)
            if location_type is None:
                location_type = cls.create_location_type()
        loc = cls.Goods.insert(type=location_type,
                               code=code,
                               container_tag=tag,
                               **fields)
        if parent is not None:
            # we insert an Apparition directly in order not to depend onto
            # Apparition working properly
            # (useful to debug Apparitiom itself if needed)
            if dt_from is None:
                dt_from = cls.dt_test1
            cls.Goods.Avatar.insert(goods=loc,
                                    state='present',
                                    location=parent,
                                    dt_from=dt_from,
                                    dt_until=None,
                                    reason=cls.Operation.Apparition.insert(
                                        goods_type=location_type,
                                        quantity=1,
                                        location=parent,
                                        dt_execution=dt_from,
                                        state='done'))
        return loc


class WmsTestCaseWithGoods(SharedDataTestCase, WmsTestCase):
    """Same as WmsTestCase with a prebaked Goods and Avatar.

    Creating an Avatar requires a reason, a location, so we have actually
    quite a few attributes:

    * ``avatar``: it is in the ``future`` state
    * ``goods``:
       actually, for now, equal to ``avatar``, but will be corrected or
       removed in a subsequent refactor (this is a leftover of the refactor
       that introduced avatars).
    * ``goods_type``
    * ``arrival``: the reason for :attr:`avatar`
    * ``incoming_loc``: where that initial Avatar dwells

    The setup of this class depends on the Arrival Operation working
    correctly, so don't use it for basic Operation tests, nor obviously for
    Arrival.
    """

    arrival_kwargs = {}

    @classmethod
    def setUpSharedData(cls):
        tz = cls.tz = FixedOffsetTimezone(0)
        cls.dt_test1 = datetime(2018, 1, 1, tzinfo=tz)
        cls.dt_test2 = datetime(2018, 1, 2, tzinfo=tz)
        cls.dt_test3 = datetime(2018, 1, 3, tzinfo=tz)

        Operation = cls.Operation
        Goods = cls.Goods
        cls.goods_type = Goods.Type.insert(label="My good type", code='MyGT')
        cls.create_location_type()
        cls.incoming_loc = cls.cls_insert_location('INCOMING')
        cls.stock = cls.cls_insert_location('STOCK')

        cls.arrival = Operation.Arrival.create(goods_type=cls.goods_type,
                                               location=cls.incoming_loc,
                                               state='planned',
                                               dt_execution=cls.dt_test1,
                                               **cls.arrival_kwargs)

        assert len(cls.arrival.outcomes) == 1
        cls.avatar = cls.arrival.outcomes[0]
        cls.goods = cls.avatar.goods
        cls.Avatar = cls.Goods.Avatar


class ConcurrencyBlokTestCase(BlokTestCase):
    """A base TestCase setting up two registries for concurrency  tests.

    This allows to make tests with two database connections (and transactions)
    and therefore check behaviour with concurrency management
    primitives, such as locks and the like.

    The second registry is initialized once for all subclasses.

    This base class introduces :meth:`setUpCommonData`, which is
    committed and means that tests using this can't run in parallel
    with others. Also, it might have side effects.

    That's the price to pay, use it only if you really want two play
    with two concurrent transactions (in the ultimate sense, the one
    seen by the database).

    TODO contribute that to AnyBlok
    """

    txn_isolation_level = 'REPEATABLE_READ'
    """The transaction isolation level to set up.

    Anyblok's default would be ``READ_UNCOMMITED``, same actually as
    its upstreams, I suppose, which is perhaps not so much what
    concurrency tests want.
    """

    registry2 = None

    @classmethod
    def additional_setting(cls):
        settings = super(ConcurrencyBlokTestCase, cls).additional_setting()
        settings['isolation_level'] = cls.txn_isolation_level
        return settings

    @classmethod
    def setUpClass(cls):
        """Prepare common data and sets the second registry up.

        The registry setup is a bit simpler than the first registry's,
        because we are sure that the database itself is ready.
        """
        super(ConcurrencyBlokTestCase, cls).setUpClass()
        cls.setUpCommonData()
        # needed because apparently we are not in a RootTransaction
        cls.registry.session.connection()._commit_impl()
        if cls.registry2 is None:
            Registry = Configuration.get('Registry', anyblok.registry.Registry)
            reg2 = Registry(cls.registry.db_name,
                            loadwithoutmigration=True,
                            **cls.registry.additional_setting)

            reg2.commit()
            # don't know why but otherwise the last_cache_id class attr
            # stays None (TODO ask jssuzanne)
            reg2.System.Cache.initialize_model()

            # on this precise class so that other subclasses can use it
            ConcurrencyBlokTestCase.registry2 = reg2

    def setUp(self):
        super(ConcurrencyBlokTestCase, self).setUp()
        self.registry2.begin_nested()

        @listens_for(self.registry2.session, "after_transaction_end")
        def restart_savepoint(session, transaction):
            if transaction.nested and not transaction._parent.nested:
                session.expire_all()
                session.begin_nested()

    def tearDown(self):
        try:
            self.registry2.System.Cache.invalidate_all()
        except sqlalchemy.exc.InvalidRequestError:  # pragma: no cover
            pass  # pragma: no cover
        finally:
            self.registry2.rollback()
            self.registry2.session.close()

        super(ConcurrencyBlokTestCase, self).tearDown()

    @classmethod
    def tearDownClass(cls):
        """Commit the removal of data shared among the two registries.
        """
        cls.removeCommonData()
        cls.registry.session.connection()._commit_impl()
        super(ConcurrencyBlokTestCase, cls).tearDownClass()

    @classmethod
    def setUpCommonData(cls):
        """Prepare the common data that's visible to both registries.

        Implementation left to subclasses, using ``cls.registry``
        (``cls.registry2`` is not even prepared at this point).
        The parent class will issue the necessary commit.

        Indeed, making concurrency tests without any shared data
        doesn't make much sense.

        Subclasses overriding this *must* also implement
        :meth:`removeCommonData` to carefully remove all that data.
        """
    @classmethod
    def removeCommonData(cls):
        """Remove all data created by :meth:`setUpCommonData`.

        subclasses **must** implement this.
        """
