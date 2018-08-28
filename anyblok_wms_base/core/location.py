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

from anyblok import Declarations

from anyblok_wms_base.constants import DATE_TIME_INFINITY

register = Declarations.register
Model = Declarations.Model


@register(Model.Wms)
class Goods:
    """Methods for Goods that are also Goods containers.

    If its :ref:`goods_type Type` has the `container=True` behaviour, then a
    Goods record is suitable as an Avatar location.

    Therefore, Goods containers form a tree-like structure (a forest).

    Downstream libraries and applications which don't want to use this
    hierarchy that comes along can do so by
    overriding :meth:`flatten_subquery`.
    """

    @classmethod
    def flatten_containers_subquery(cls, top=None,
                                    container_types=None,
                                    exclude_container_types=None,
                                    additional_states=None, at_datetime=None):
        """Return an SQL subquery flattening the containment graph.

        Containing Goods can themselves be placed within a container
        through the standard mechanism: by having an Avatar whose location is
        the surrounding container.
        This default implementation issues a recursive CTE (``WITH RECURSIVE``)
        that climbs down along this, returning just the ``id`` column


        This subquery cannot be used directly: it is meant to be used as part
        of a wider query; see unit tests (``test_location``) for nice examples
        with or without joins.

        .. note:: This subquery itself does not restrict its results to
                  actually be containers! Only its use in joins as locations
                  of Avatars will, and that's considered good enough, as
                  filtering on actual containers would be more complicated
                  (resolving behaviour inheritance) and is useless for
                  quantity queries.

                  Applicative code relying on this method for other reasons
                  than quantity counting should therefore add its own ways
                  to restrict to actual containers if needed.

        :param top:
           if specified, the query starts at this Location (inclusive)

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
        cte = cls.query(cls.id)
        if top is None:
            cte = cte.outerjoin(Avatar, Avatar.goods_id == cls.id).filter(
                Avatar.location_id.is_(None))
        else:
            cte = cte.filter_by(id=top.id)

        cte = cte.cte(name="container", recursive=True)
        parent = orm.aliased(cte, name='parent')
        child = orm.aliased(cls, name='child')
        tail = query(child.id).join(
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

    def is_container(self):
        return self.type.is_container()
