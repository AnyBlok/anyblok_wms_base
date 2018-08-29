# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from sqlalchemy import or_
from sqlalchemy import not_
from sqlalchemy import func
from sqlalchemy import orm
from anyblok import Declarations
from anyblok_wms_base.constants import DATE_TIME_INFINITY

register = Declarations.register
Model = Declarations.Model

_missing = object()
"""Marker to know that a kwarg is not passed if ``None`` means something else.
"""


@register(Model)
class Wms:
    """Namespace for WMS related models and transversal methods.

    Since this Model does not have any persistent data, making instances of
    it is mostly irrelevant, and therefore, the transversal methods are
    classmethods.
    """

    @classmethod
    def quantity(cls,
                 goods_type=None,
                 additional_states=None,
                 at_datetime=None,
                 additional_filter=None,
                 location=None,
                 location_recurse=True):
        """Compute the quantity of PhysObj meeting various criteria.

        The computation actually involves querying :class:`Avatars
        <anyblok_wms_base.core.goods.Avatar>`, which hold the
        information about location, states and date/time.

        :param goods_type:
            if specified, restrict computation to PhysObj of this type
        :param location:
            if specified, restrict computation to PhysObj Avatars
            from that location (see also ``location_recurse`` below)
        :param bool location_recurse:
            If ``True``, and ``location`` is specified, the PhysObj Avatars
            from sublocations of ``location`` will be taken recursively into
            account.
        :param additional_filter:
           optional function to restrict the PhysObj Avatars to take into
           account. It applies to the outer query, i.e., not within
           the containers recursions.

           The :meth:`restrict_container_types` and
           :meth:`exclude_container_types` provided methods return functions
           that are meant to be used with this parameter.

           In general, the passed function must have the following signature::

                def additional_filter(query):
                   filtered_query = ...
                   return filtered_query

           where ``query`` is a query object involving Avatars.

           .. seealso:: :meth:`filter_container_types` for a working example.


           .. warning:: any JOINs that this function introduces
                        *should be aliased* to avoid conflicting with the
                        ones already present in ``query``.

        :param additional_states:
            Optionally, states of the PhysObj Avatar to take into account
            in addition to the ``present`` state.

            Hence, for ``additional_states=['past']``, we have the
            PhysObj Avatars that were already there and still are,
            as well as those that aren't there any more,
            and similarly for 'future'.
        :param at_datetime:
            take only into account PhysObj Avatar whose date-time range
            contains the specified value.

            ``anyblok_wms_base.constants.DATE_TIME_INFINITY``
            can in particular be used to consider only those
            Avatars whose ``dt_until`` is ``None``.

            This parameter is mandatory if ``additional_states`` is specified.

        TODO: provide filtering according to PhysObj properties (should become
        special PostgreSQL JSON clauses)

        TODO: provide a way to add more criteria from optional Bloks, e.g,
        ``wms-reservation`` could add a way to filter only unreserved PhysObj.

        TODO PERF: for timestamp ranges, use GiST indexes and the @> operator.
        See the comprehensive answer to `that question
        <https://dba.stackexchange.com/questions/39589>`_ for an entry point.
        Let's get a DB with serious volume and datetimes first.
        """
        PhysObj = cls.registry.Wms.PhysObj
        Avatar = PhysObj.Avatar
        query = cls.base_quantity_query()
        if goods_type is not None:
            query = query.filter(PhysObj.type == goods_type)

        if location is not None:
            if location_recurse:
                cte = PhysObj.flatten_containers_subquery(
                    top=location,
                    at_datetime=at_datetime,
                    additional_states=additional_states)
                query = query.join(cte, cte.c.id == Avatar.location_id)
            else:
                query = query.filter(Avatar.location == location)

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
        if additional_filter is not None:
            query = additional_filter(query)
        res = query.one()[0]
        return 0 if res is None else res

    @classmethod
    def base_quantity_query(cls):
        """Return base join query, without any filtering

        :return: The query is assumed to produce exactly one row, with the
                 wished quantity result (possibly ``None`` for 0)
        """
        Avatar = cls.PhysObj.Avatar
        return Avatar.query(func.count(Avatar.id)).join(Avatar.goods)

    @classmethod
    def filter_container_types(cls, types):
        """Allow restricting container types in quantity queries.

        :return: a suitable filtering function that restricts the counted
                 Avatars to those whose *direct* location is of the given
                 types.
        """
        PhysObj = cls.registry.Wms.PhysObj
        Avatar = PhysObj.Avatar
        loc_goods = orm.aliased(PhysObj, name='location_goods')

        def add_filter(query):
            return query.join(loc_goods, Avatar.location).filter(
                loc_goods.type_id.in_(set(t.id for t in types)))

        return add_filter

    @classmethod
    def exclude_container_types(cls, types):
        """Allow restricting container types in quantity queries.

        :return: a suitable filtering function that restricts the counted
                 Avatars to those whose *direct* location is not of
                 the given types.
        """
        PhysObj = cls.registry.Wms.PhysObj
        Avatar = PhysObj.Avatar
        loc_goods = orm.aliased(PhysObj, name='location_goods')

        def add_filter(query):
            joined = query.join(loc_goods, Avatar.location)
            if len(types) == 1:
                # better for SQL indexes
                return joined.filter(loc_goods.type_id != types[0].id)
            else:
                return joined.filter(
                    not_(loc_goods.type_id.in_(set(t.id for t in types))))

        return add_filter

    @classmethod
    def create_root_container(cls, container_type, **fields):
        """Helper to create topmost containers.

        Topmost containers must have themselves no surrounding container,
        which means they can't have Avatars, and therefore can't be outcomes
        of any Operations, which is quite exceptional in Anyblok / Wms Base.

        On the other hand, at least one
        such container is needed to root the containing hierarchy.

        :param container_type: a :ref:`PhysObj Type <goods_type>` that's
                               suitable for containers.
        :return: the created container
        """
        if container_type is None or not container_type.is_container():
            raise ValueError(
                "Not a proper container type: %r " % container_type)
        return cls.registry.Wms.PhysObj.insert(type=container_type,
                                               **fields)
