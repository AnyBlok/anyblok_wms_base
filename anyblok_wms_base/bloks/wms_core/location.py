# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from sqlalchemy import orm
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import literal

from anyblok import Declarations
from anyblok.column import String
from anyblok.column import Text
from anyblok.column import Integer
from anyblok.relationship import Many2One

from anyblok_wms_base.constants import DATE_TIME_INFINITY

register = Declarations.register
Model = Declarations.Model


_missing = object()
"""Marker to know that a kwarg is not passed if ``None`` means something else.
"""


@register(Model.Wms)
class Location:
    """A stock location.

    TODO add location types to encode behavioral properties (internal, EDI,
    stuff like size ?)
    """
    id = Integer(label="Identifier", primary_key=True)
    code = String(label="Identifying code")  # TODO index
    label = String(label="Label")
    parent = Many2One(label="Parent location",
                      model='Model.Wms.Location')
    tag = Text()
    """Tag for Quantity grouping.

    This field is a kind of tag that can be used to filter in quantity
    queries. It allows for location-based assessment of stock levels by
    recursing in the hierarchy while still allowing exceptions: to discard or
    include sublocations.

    For instance, one may represent a big warehouse as having several rooms
    (R1, R2)
    each one with an examination area (R1/QA, R2/QA), which can be further
    subdivided.

    Goods stored in the workshop are not to be sold, except maybe those that
    are in the waiting area before been put back in stock (R1/QA/Good etc.).

    It's then useful to tag Rooms as 'sellable', but in them, QA locations as
    'qa', and finally the good waiting areas as 'sellable' again.

    See in unit tests for a demonstration of that.
    """

    def __str__(self):
        return ("(id={self.id}, code={self.code!r}, "
                "label={self.label!r})".format(self=self))

    def __repr__(self):
        return "Wms.Location" + str(self)

    def resolve_tag(self):
        """Return self.tag, or by default ancestor's."""
        # TODO make a recursive query for this also
        if self.tag is not None:
            return self.tag
        if self.parent is None:
            return None
        return self.parent.resolve_tag()

    def quantity(self, goods_type,
                 additional_states=None,
                 at_datetime=None,
                 location_tag=_missing,
                 recursive=True):
        """Return the full quantity in location for the given type.

        :param bool recursive:
            If ``True``, the Goods Avatars from sublocations will be taken
            into account.
        :param str location_tag:
            If passed, only the Goods Avatars sitting in a Location having
            or inheriting this tag will be taken into account (may seem only
            useful if ``recursive`` is ``True``, yet the non-recursive case
            behaves consistently).
        :param additional_states:
            Optionally, states of the Goods Avatar to take into account
            in addition to the ``present`` state.

            Hence, for ``additional_states=['past']``, we have the
            Goods Avatars that were already there and still are,
            as well as those that aren't there any more,
            and similarly for 'future'.
        :param at_datetime:
            take only into account Goods Avatar whose date-time range
            contains the specified value.

            ``anyblok_wms_base.constants.DATE_TIME_INFINITY``
            can in particular be used to consider only those
            Avatars whose ``dt_until`` is ``None``.

            This parameter is mandatory if ``additional_states`` is specified.

        TODO: provide filtering according to Goods properties (should become
        special PostgreSQL JSON clauses)

        TODO PERF: for timestamp ranges, use GiST indexes and the @> operator.
        See the comprehensive answer to `that question
        <https://dba.stackexchange.com/questions/39589>`_ for an entry point.
        Let's get a DB with serious volume and datetimes first.
        """
        Goods = self.registry.Wms.Goods
        Avatar = Goods.Avatar
        query, use_count = self.base_quantity_query()
        query = query.filter(Goods.type == goods_type)

        # location_tag needs the recursive CTE even if the
        # quantity request is not recursive (so that tag is the correct one).
        if recursive or location_tag is not _missing:
            cte = self.tag_cte(top=self)
            query = query.join(cte, cte.c.id == Avatar.location_id)

        if not recursive:
            query = query.filter(Avatar.location == self)

        if location_tag is not _missing:
            query = query.filter(cte.c.tag == location_tag)

        if additional_states is None:
            query = query.filter(Avatar.state == 'present')
        else:
            states = ('present',) + tuple(additional_states)
            query = query.filter(Avatar.state.in_(states))
            if at_datetime is None:
                raise ValueError(
                    "Querying quantities with additional states {!r} requires "
                    "to specify the 'at_datetime' kwarg".format(
                        additional_states))

        if at_datetime is DATE_TIME_INFINITY:
            query = query.filter(Avatar.dt_until.is_(None))
        elif at_datetime is not None:
            query = query.filter(Avatar.dt_from <= at_datetime,
                                 or_(Avatar.dt_until.is_(None),
                                     Avatar.dt_until > at_datetime))
        if use_count:
            return query.count()

        res = query.one()[0]
        return 0 if res is None else res

    @classmethod
    def base_quantity_query(cls):
        """Return base join query, without any filtering, and eval indication.

        :return: query, ``True`` if ``count()`` is to be used. Otherwise,
                 the query is assumed to produce exactly one row, with the
                 wished quantity result (possibly ``None`` for 0)
        """
        Avatar = cls.registry.Wms.Goods.Avatar
        return Avatar.query().join(Avatar.goods), True

    @classmethod
    def tag_cte(cls, top=None, resolve_top_tag=True):
        """Return an SQL CTE that recurses in the hierarchy, defaulting tags.

        The defaulting tag policy is that a Location whose tag is ``None``
        inherits its parent's.

        The CTE cannot be used directly, but see unit tests for nice examples
        with or without joins.

        For some applications with a large and complicated Location hierarchy,
        joining on this CTE can become a performance problem. Quoting
        `PostgreSQL documentation on CTEs
        <https://www.postgresql.org/docs/10/static/queries-with.html>`_:

          However, the other side of this coin is that the optimizer is less
          able to push restrictions from the parent query down into a WITH
          query than an ordinary subquery.
          The WITH query will generally be evaluated as written,
          without suppression of rows that the parent query might
          discard afterwards.

        If that becomes a problem, it is still possible to override the
        present method: any subquery whose results have the ``id`` and
        ``tag`` columns can be used by callers instead of the recursive CTE.

        Examples:

        1. one might design a flat Location hierarchy using prefixing on
           :attr:`code` to express inclusion instead of the provided
           :attr:`parent`
        2. one might make a materialized view out of this very CTE,
           refreshing as soon as needed.
        """
        query = cls.registry.session.query

        if top is not None and top.tag is None:
            init_tag = top.resolve_tag()
            cte = cls.query(cls.id, literal(init_tag).label('tag'))
        else:
            cte = cls.query(cls.id, cls.tag)
        if top is None:
            cte = cte.filter(cls.parent == top)  # doesn't work with is_()
        else:
            # starting with top, not its children so that the children
            # can inherit tag from top (done in the recursive part of the
            # subquery)
            cte = cte.filter(cls.id == top.id)
        cte = cte.cte(name="location_tag", recursive=True)
        parent = orm.aliased(cte, name='parent')
        child = orm.aliased(cls, name='child')
        cte = cte.union_all(
            query(child.id,
                  func.coalesce(child.tag, parent.c.tag).label('tag')).filter(
                      child.parent_id == parent.c.id))
        return cte
