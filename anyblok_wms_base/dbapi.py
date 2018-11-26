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
import psycopg2
from psycopg2.extras import DateTimeTZRange  # noqa (reexport)


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


def cast_tstz(value, cr):
    if value == "infinity":
        return DATE_TIME_INFINITY
    return psycopg2.extensions.PYDATETIMETZ(value, cr)

from psycopg2.extensions import string_types

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
