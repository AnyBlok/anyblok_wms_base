# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
import itertools

_missing = object()
"""A marker to use as default value in get-like functions/methods."""


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


def dict_merge(first, second, list_merge=None, path=()):
    """Deep merging of two Python objects

    :param first: the one having precedence.
    :param list_merge: controls list merging. This is a dict
       whose keys are paths (tuple of keys or indices) from the top and
       values can be:

        + None: ``first`` is returned
        + 'zip': return the list obtained by merging elements of
                 the first list with the second, in order.
        + 'append': ``first`` elements are added at the end of ``second``
        + 'append': ``first`` elements are added at the beginning of
                    ``second``
        + 'set': a set is built with ``first`` and ``second`` elements.
    :param path: internal accumulator

    if both parameters are :class:`dict` or :class:`set` instances,
    they get merged, recursively for dicts. Otherwise the value of ``first``
    is returned.

    No attempt is made to merge tuples (could be done later)

    *Examples and tests*

    We'll need pretty printing to compare dicts::

      >>> from pprint import pprint

    First order merging:

      >>> pprint(dict_merge(dict(a=1), dict(b=2)))
      {'a': 1, 'b': 2}

    Recursion::

      >>> pprint(dict_merge(dict(a=1, deep=dict(k='foo')),
      ...                   dict(a=2, deep=dict(k='bar', other=3))))
      {'a': 1, 'deep': {'k': 'foo', 'other': 3}}
      >>> pprint(dict_merge([dict(a=1, b=2), dict(a=3)],
      ...                   [dict(b=5), dict(b=6)],
      ...                   list_merge={(): 'zip'}))
      [{'a': 1, 'b': 2}, {'a': 3, 'b': 6}]
      >>> pprint(dict_merge(dict(tozip=[dict(a=1, b=2), dict(a=3)], x=[1]),
      ...                   dict(tozip=[dict(b=5), dict(b=6)], x=[2]),
      ...                   list_merge={('tozip', ): 'zip',}))
      {'tozip': [{'a': 1, 'b': 2}, {'a': 3, 'b': 6}], 'x': [1]}

    Sets::

      >>> s = dict_merge({'a', 'c'}, {'a', 'b'})
      >>> type(s)
      <class 'set'>
      >>> sorted(s)
      ['a', 'b', 'c']

    Lists::

      >>> dict_merge(['a'], ['b'], list_merge={(): 'append'})
      ['b', 'a']
      >>> dict_merge(['a'], ['b'], list_merge={(): 'prepend'})
      ['a', 'b']
      >>> s = dict_merge(['a', 'b'], ['a', 'c'], list_merge={(): 'set'})
      >>> type(s)
      <class 'set'>
      >>> sorted(s)
      ['a', 'b', 'c']

    Recursion inside a zip:

      >>> dict_merge([dict(x='a'), dict(y=[1]), {}],
      ...            [dict(x='b'), dict(y=[2]), dict(x=1)],
      ...            list_merge={(): 'zip',
      ...                        (1, 'y'): 'append'})
      [{'x': 'a'}, {'y': [2, 1]}, {'x': 1}]

    Non dict values::

      >>> dict_merge(1, 2)
      1
      >>> dict_merge(dict(a=1), 'foo')
      {'a': 1}
      >>> dict_merge('foo', dict(a=1))
      'foo'


    """
    if isinstance(first, list) and isinstance(second, list):
        return _dict_list_merge(first, second,
                                list_merge=list_merge,
                                path=path)

    if isinstance(first, set) and isinstance(second, set):
        s = second.copy()
        s.update(first)
        return s

    if not isinstance(first, dict) or not isinstance(second, dict):
        return first

    res = second.copy()
    for k, firstv in first.items():
        secondv = second.get(k, _missing)
        if secondv is _missing:
            res[k] = firstv
        else:
            res[k] = dict_merge(firstv, secondv,
                                list_merge=list_merge,
                                path=path + (k, ))

    return res


def _dict_list_merge(first, second, list_merge=None, path=()):
        if list_merge is None:
            return first

        lm = list_merge.get(path)
        if lm == 'zip':
            return [dict_merge(x, y,
                               list_merge=list_merge,
                               path=path + (i, ))
                    for i, (x, y) in enumerate(zip(first, second))]
        elif lm == 'append':
            return second + first
        elif lm == 'prepend':
            return first + second
        elif lm == 'set':
            s = set(first)
            s.update(second)
            return s

        return first


class NonZero:
    """Marker to mean any unspecified non zero value.

    >>> str(NonZero())
    'NONZERO'
    >>> bool(NonZero())
    True
    >>> NonZero() == 2
    True
    >>> NonZero() == 0
    False
    >>> NonZero() != 0
    True
    >>> NonZero() != 2
    False
    >>> try: NonZero() == 'abc'
    ... except ValueError: print('ok')
    ok

    We don't implement __repr__ because with reloads and the like, one
    can have subtle bugs with constants, and in that case, the default
    ``repr()`` including the object id (memory address with CPython)
    is really useful.

    For these subtle bugs reasons, it's probably better to test with
    ``isinstance`` rather than with ``is`` on a constant.
    """

    def __str__(self):
        return "NONZERO"

    def __bool__(self):
        return True

    def __eq__(self, other):
        if other == 0:
            return False
        if not isinstance(other, NonZero) and not isinstance(other, int):
            raise ValueError("Can't compare NonZero() to %r" % other)
        return True
