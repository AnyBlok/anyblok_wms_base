# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from sqlalchemy import or_
from sqlalchemy import func
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
                 location=None,
                 location_recurse=True,
                 location_tag=_missing):
        """Compute the quantity of Goods meeting various criteria.

        The computation actually involves querying :class:`Avatars
        <anyblok_wms_base.core.goods.Avatar>`, which hold the
        information about location, states and date/time.

        :param goods_type:
            if specified, restrict computation to Goods of this type
        :param location:
            if specified, restrict computation to Goods Avatars
            from that location (see also ``location_recurse`` below)
        :param bool location_recurse:
            If ``True``, and ``location`` is specified, the Goods Avatars
            from sublocations of ``location`` will be taken recursively into
            account.
        :param str location_tag:
            If passed, only the Goods Avatars sitting in a location having
            or inheriting this tag will be taken into account (may seem only
            useful if ``location_recurse`` is ``True``, yet the non-recursive
            case behaves consistently).
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

        TODO: provide a way to add more criteria from optional Bloks, e.g,
        ``wms-reservation`` could add a way to filter only unreserved Goods.

        TODO PERF: for timestamp ranges, use GiST indexes and the @> operator.
        See the comprehensive answer to `that question
        <https://dba.stackexchange.com/questions/39589>`_ for an entry point.
        Let's get a DB with serious volume and datetimes first.
        """
        Goods = cls.registry.Wms.Goods
        Avatar = Goods.Avatar
        query = cls.base_quantity_query()
        if goods_type is not None:
            query = query.filter(Goods.type == goods_type)

        # location_tag needs the recursive CTE even if the
        # quantity request is not recursive (so that tag is the correct one).
        if ((location is not None and location_recurse) or
                location_tag is not _missing):
            cte = Goods.flatten_subquery_with_tags(
                top=location,
                at_datetime=at_datetime,
                additional_states=additional_states)
            query = query.join(cte, cte.c.id == Avatar.location_id)

        if location is not None and not location_recurse:
            query = query.filter(Avatar.location == location)

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
        res = query.one()[0]
        return 0 if res is None else res

    @classmethod
    def base_quantity_query(cls):
        """Return base join query, without any filtering

        :return: The query is assumed to produce exactly one row, with the
                 wished quantity result (possibly ``None`` for 0)
        """
        Avatar = cls.Goods.Avatar
        return Avatar.query(func.count(Avatar.id)).join(Avatar.goods)

    @classmethod
    def create_root_container(cls, container_type, **fields):
        """Helper to create topmost containers.

        Topmost containers must have themselves no surrounding container,
        which means they can't have Avatars, and therefore can't be outcomes
        of any Operations, which is quite exceptional in Anyblok / Wms Base.

        On the other hand, at least one
        such container is needed to root the containing hierarchy.

        :param container_type: a :ref:`Goods Type <goods_type>` that's
                               suitable for containers.
        :return: the created container
        """
        if container_type is None or not container_type.is_container():
            raise ValueError(
                "Not a proper container type: %r " % container_type)
        return cls.registry.Wms.Goods.insert(type=container_type,
                                             **fields)
