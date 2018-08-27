# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from sqlalchemy import orm
from sqlalchemy import or_
from sqlalchemy import func
from sqlalchemy import literal

from anyblok import Declarations
from anyblok.column import Text

from anyblok_wms_base.constants import DATE_TIME_INFINITY

register = Declarations.register
Model = Declarations.Model


@register(Model.Wms)
class Goods:
    """Methods for Goods that are also Goods containers.

    If its :ref:`goods_type Type` has the `container=True` behaviour, then a
    Goods record is suitable as an Avatar location.

    Therefore, Goods containers form a tree-like structure (a forest).

    Goods containers also have a ``container_tag`` property,
    which can be used to express functional meaning, especially for
    :meth:`quantity computations
    <anyblok_wms_base.core.wms.Wms.quantity>`.

    Downstream libraries and applications which don't want to use this
    hierarchy and the defaulting of tags that comes along can do so by
    overriding :meth:`flatten_hierarchy_with_tags` and :meth:`resolve_tag`
    """
    container_tag = Text()
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

    def resolve_tag(self):
        """Return self.tag, or by default ancestor's."""
        # TODO make a recursive query for this also
        if self.container_tag is not None:
            return self.container_tag
        # TODO this should be done at a certain date, too, with
        # appropriate states
        av = self.Avatar.query().filter_by(
            goods=self, state='present').first()
        if av is None:
            return None
        return av.location.resolve_tag()

    @classmethod
    def flatten_subquery_with_tags(cls, top=None, resolve_top_tag=True,
                                   additional_states=None, at_datetime=None):
        """Return an SQL subquery flattening the hierarchy, resolving tags.

        The resolving tag policy is that a Location whose tag is ``None``
        inherits its parent's.

        This subquery cannot be used directly: it is meant to be used as part
        of a wider query; see unit tests (``test_location``) for nice examples
        with or without joins. It has two columns: ``id`` and ``tag``.

        :param top:
           if specified, the query starts at this Location (inclusive)

        Containing Goods can themselves be placed within a container
        through the standard mechanism: by having an Avatar whose location is
        the surrounding container.
        This default implementation issues a recursive CTE (``WITH RECURSIVE``)
        that climbs down along this.

        For some applications with a large and complicated containing
        hierarchy, joining on this CTE can become a performance problem.
        Quoting
        `PostgreSQL documentation on CTEs
        <https://www.postgresql.org/docs/10/static/queries-with.html>`_:

          However, the other side of this coin is that the optimizer is less
          able to push restrictions from the parent query down into a WITH
          query than an ordinary subquery.
          The WITH query will generally be evaluated as written,
          without suppression of rows that the parent query might
          discard afterwards.

        If that becomes a problem, it is still possible to override the
        present method: any subquery whose results have the same columns
        can be used by callers instead of the recursive CTE.

        Examples:

        1. one might design a flat Location hierarchy using prefixing on
           :attr:`code` to express inclusion instead of the standard Avatar
           mechanism.
           :attr:`parent`. See :meth:`anyblok_wms_base.core.tests
           .test_location.test_override_tag_recursion` for a proof of concept
           of this.
        2. one might make a materialized view out of the present recursive CTE,
           refreshing as soon as needed.
        """
        Avatar = cls.Avatar
        query = cls.registry.session.query

        if top is not None and top.container_tag is None:
            init_tag = top.resolve_tag()
            cte = cls.query(cls.id, literal(init_tag).label('tag'))
        else:
            cte = cls.query(cls.id, cls.container_tag.label('tag'))
        if top is None:
            cte = cte.outerjoin(Avatar, Avatar.goods_id == cls.id).filter(
                Avatar.location_id.is_(None))
        else:
            # starting with top, not its children so that the children
            # can inherit tag from top (done in the recursive part of the
            # subquery)
            cte = cte.filter(cls.id == top.id)
        cte = cte.cte(name="location_tag", recursive=True)
        parent = orm.aliased(cte, name='parent')
        child = orm.aliased(cls, name='child')
        tail = query(child.id,
                     func.coalesce(child.container_tag, parent.c.tag)
                     .label('tag')).join(
                         Avatar, Avatar.goods_id == child.id).filter(
                             Avatar.location_id == parent.c.id)
        # taking additional states and datetime query into account
        # TODO, this location part is very redundant with what's done in
        # Wms.quantity() itself for the Goods been counted, we should refactor
        if additional_states is None:
            tail = tail.filter(Avatar.state == 'present')
        else:
            tail = tail.filter(Avatar.state.in_(
                ('present', ) + tuple(additional_states)))

        if at_datetime is DATE_TIME_INFINITY:
            tail = tail.filter(Avatar.dt_until.is_(None))
        elif at_datetime is not None:
            tail = tail.filter(Avatar.dt_from <= at_datetime,
                               or_(Avatar.dt_until.is_(None),
                                   Avatar.dt_until > at_datetime))
        cte = cte.union_all(tail)
        return cte
