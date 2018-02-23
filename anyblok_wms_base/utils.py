# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
import itertools


def min_upper_bounds(inputs):
    """Return the smallest of the given inputs, each thought as an upper bound.

    :param untils: an iterable of comparable values or ``None``

    To thinking about the inputs as some upper bounds translates as
    the convention that ``None`` means +infinity.

    >>> min_upper_bounds([2, 1, None])
    1
    >>> min_upper_bounds([None, None]) is None
    True
    >>> min_upper_bounds(x for x in [2, 5, 3])
    2
    """
    res = None
    # ValueError for min(()) isn't sanely catcheable, that'd been leaner
    for inp in itertools.filterfalse(lambda i: i is None, inputs):
        if res is None or inp < res:
            res = inp
    return res
