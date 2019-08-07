# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
"""DBAPI Adapters customization.

This module encapsulates all assumptions and alterations of the low level
DBAPI adapter in use.

In particular, supporting a new DBAPI adapter such as pygresql should
involve modifying this module only.
"""
from datetime import (
    timezone,
)
import psycopg2
from psycopg2.extras import DateTimeTZRange as TimeSpan

EMPTY_TIMESPAN = TimeSpan(empty=True)


class DbConstant:

    def __init__(self, dbrepr, as_str=None):
        self.dbrepr = dbrepr
        self.as_str = dbrepr.decode() if as_str is None else as_str

    def __repr__(self):
        return 'DbConstant(%r)' % self.dbrepr

    def __str__(self):
        return self.as_str


DATE_TIME_INFINITY = DbConstant(b"'infinity'::timestamptz")
"""A marker used to represent +infinity date/time.

For instance, if a method is used to query Avatars for a given date, using
this marker in the interface is more explicit than using None (which could
also mean one does not care about dates).
"""

DATE_TIME_INFINITY.tzinfo = timezone.utc

# partial support for comparison
#  This works only with the constant in left-hand side; Python seems to have
#  some capabilities to flip the comparison over, but not in this case
DATE_TIME_INFINITY.__ge__ = lambda x: True
DATE_TIME_INFINITY.__gt__ = lambda x: x is not DATE_TIME_INFINITY
DATE_TIME_INFINITY.__le__ = lambda x: x is DATE_TIME_INFINITY
DATE_TIME_INFINITY.__lt__ = lambda x: False

ts_orig_contains = TimeSpan.__contains__


def ts_contains(ts, dt):
    """Monkey-patch of the 'in' operator of TimeSpan to deal with infinity.

    Necessary because the partial comparison support doesn't work with
    infinity in the right hand side.

    >>> inf = DATE_TIME_INFINITY  # shortcut
    >>> from datetime import datetime
    >>> dt = datetime(2001, 4, 7, tzinfo=timezone.utc)
    >>> later = datetime(2002, 1, 1, tzinfo=timezone.utc)

    >>> finite = TimeSpan(lower=dt, upper=later, bounds='[)')
    >>> inf in finite
    False

    >>> unbounded = TimeSpan(lower=dt, upper=inf, bounds='[)')
    >>> later in unbounded
    True
    >>> DATE_TIME_INFINITY in unbounded
    False

    >>> bounded = TimeSpan(lower=dt, upper=inf, bounds='[]')
    >>> later in bounded
    True
    >>> DATE_TIME_INFINITY in bounded
    True

    >>> shorter = TimeSpan(lower=later, upper=inf, bounds='[]')
    >>> dt in shorter
    False
    >>> later in shorter
    True

    >>> shorter_excl = TimeSpan(lower=later, upper=inf, bounds='(]')
    >>> dt in shorter_excl
    False
    >>> later in shorter_excl
    False
    >>> DATE_TIME_INFINITY in shorter_excl
    True
    """
    if dt is DATE_TIME_INFINITY:
        return ts.upper is DATE_TIME_INFINITY and ts.upper_inc
    elif ts.upper is DATE_TIME_INFINITY:
        if ts.lower is DATE_TIME_INFINITY:
            return False
        return (ts.lower_inc and dt >= ts.lower) or dt > ts.lower

    return ts_orig_contains(ts, dt)


TimeSpan.__contains__ = ts_contains


def cast_tstz(value, cr):
    if value == "infinity":
        return DATE_TIME_INFINITY
    return psycopg2.extensions.PYDATETIMETZ(value, cr)


TSTZ_WITH_INFINITY = psycopg2.extensions.new_type(
    psycopg2.extensions.PYDATETIMETZ.values,
    'TSTZ_WITH_INFINITY',
    cast_tstz)
psycopg2.extensions.register_type(TSTZ_WITH_INFINITY)


class DbConstantAdapter:
    """Proper conversion of DATE_TIME_INFINITY.

    .. seealso::

        The official Psycopg `instructions
        <http://initd.org/psycopg/docs/usage.html#infinite-dates-handling>`
    """
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def getquoted(self):
        return self.wrapped.dbrepr


psycopg2.extensions.register_adapter(DbConstant, DbConstantAdapter)
