# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok.tests.testcase import BlokTestCase


class WmsTestCase(BlokTestCase):
    """Provide some common utilities.

    Probably some of these should be contributed back into Anyblok, but
    we'll see.
    """

    def single_result(self, query):
        """Assert that query as a single result and return it.

        This is better than one() in that it will issue a Failure instead of
        an error.
        """
        results = query.all()
        self.assertEqual(len(results), 1)
        return results[0]
