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


def dict_merge(first, second, list_merge=None):
    """Deep merging of two Python objects

    if both parameters are :class:`dict` or :class:`set` instances,
    they get merged, recursively for dicts. Lists can be merged according
    to the specified ``list_merge``. Otherwise the value of ``first``
    is returned.

    :param first: the one having precedence.
    :param list_merge: controls list merging.
       If ``first`` and ``second`` are lists, this is a pair whose first
       element specifies what to do of lists at top level, with possible
       values:

       + ``None``:
         ``first`` is returned
       + ``'zip'``:
         return the list obtained by merging elements of the first list with
         those of the second, in order.
       + ``'append'``:
         elements of ``first`` are added in order at the end of ``second``.
       + ``'prepend'``:
         elements of ``first`` are inserted in order at the beginning
         of ``second``.
       + ``'set'``:
         a :class:`set` is built from elements of ``first`` and ``second``.

       The second element of ``list_merge`` is then for recursing:
       a :class:`dict` whose keys
       are list indexes or the ``'*'`` wildcard and values are to be passed
       as ``list_merge`` below. The second element can also be ``None``,
       behaving like an empty :class:`dict`.

       If ``first`` and ``second`` are :class:`dicts <dict>`, then
       ``list_merge`` is directly the ``dict`` for recursion, and its keys
       are those of ``first`` and ``second``.

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
      ...                   list_merge=('zip', None)))
      [{'a': 1, 'b': 2}, {'a': 3, 'b': 6}]
      >>> pprint(dict_merge(dict(tozip=[dict(a=1, b=2), dict(a=3)], x=[1]),
      ...                   dict(tozip=[dict(b=5), dict(b=6)], x=[2]),
      ...                   list_merge=dict(tozip=('zip', None))))
      {'tozip': [{'a': 1, 'b': 2}, {'a': 3, 'b': 6}], 'x': [1]}
      >>> pprint(dict_merge(dict(tozip=[dict(a=1, b=2), dict(a=3)], x=[1]),
      ...                   dict(tozip=[dict(b=5), dict(b=6)], x=[2]),
      ...                   list_merge={'tozip': ('zip', None),
      ...                               '*': ('set', None),
      ...                               }))
      {'tozip': [{'a': 1, 'b': 2}, {'a': 3, 'b': 6}], 'x': {1, 2}}

    Sets::

      >>> s = dict_merge({'a', 'c'}, {'a', 'b'})
      >>> type(s)
      <class 'set'>
      >>> sorted(s)
      ['a', 'b', 'c']

    Lists::

      >>> dict_merge(['a'], ['b'])
      ['a']
      >>> dict_merge(['a'], ['b'], list_merge=(None, None))
      ['a']
      >>> dict_merge(['a'], ['b'], list_merge=('append', None))
      ['b', 'a']
      >>> dict_merge(['a'], ['b'], list_merge=('prepend', None))
      ['a', 'b']
      >>> s = dict_merge(['a', 'b'], ['a', 'c'], list_merge=('set', None))
      >>> type(s)
      <class 'set'>
      >>> sorted(s)
      ['a', 'b', 'c']

    Recursion inside a zip:

      >>> dict_merge([dict(x='a'), dict(y=[1]), {}],
      ...            [dict(x='b'), dict(y=[2]), dict(x=1)],
      ...            list_merge=('zip',
      ...                        {1: {'y': ('append', None)}}))
      [{'x': 'a'}, {'y': [2, 1]}, {'x': 1}]

    Wildcards in ``list_merge`` for lists::

      >>> dict_merge([dict(y=['a']), dict(y=[1]), {}],
      ...            [dict(y=['b']), dict(y=[2]), dict(y=3)],
      ...            list_merge=('zip',
      ...                        {'*': {'y': ('append', None)}}))
      [{'y': ['b', 'a']}, {'y': [2, 1]}, {'y': 3}]

    Non dict values::

      >>> dict_merge(1, 2)
      1
      >>> dict_merge(dict(a=1), 'foo')
      {'a': 1}
      >>> dict_merge('foo', dict(a=1))
      'foo'

    If ``first`` is None, second is always returned. This spares the caller
    a useless empty :class:`dict` creation in many cases.

      >>> dict_merge(None, 1)
      1
      >>> dict_merge(None, dict(x=1))
      {'x': 1}

    """
    if first is None:
        return second

    if isinstance(first, list) and isinstance(second, list):
        return _dict_list_merge(first, second,
                                list_merge=list_merge)

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
                                list_merge=_wild_get(list_merge, k))

    return res


def _wild_get(spec, k):
    """Getting a value in a dict, defaulting with the wildcard key.

    Also treats the case where ``spec`` is ``None``

    Examples::

      >>> _wild_get(None, 'foo') is None
      True
      >>> d = {'*': 2, 'a': 1}
      >>> _wild_get(d, 'a')
      1
      >>> _wild_get(d, 'foo')
      2
    """
    if spec is None:
        return None
    v = spec.get(k)
    if v is not None:
        return v
    return spec.get('*')


def _dict_list_merge(first, second, list_merge=None):
    if list_merge is None:
        return first

    lm, below = list_merge
    if lm == 'zip':
        return [dict_merge(x, y,
                           list_merge=_wild_get(below, i))
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
