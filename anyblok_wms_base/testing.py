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
from anyblok.tests.testcase import BlokTestCase


class WmsTestCase(BlokTestCase):
    """Provide some common utilities.

    Probably some of these should be contributed back into Anyblok, but
    we'll see.
    """

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
