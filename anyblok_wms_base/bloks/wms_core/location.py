# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from sqlalchemy import func
from sqlalchemy import or_
from anyblok import Declarations
from anyblok.column import String
from anyblok.column import Integer
from anyblok.relationship import Many2One

register = Declarations.register
Model = Declarations.Model


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

    def __str__(self):
        return ("(id={self.id}, code={self.code!r}, "
                "label={self.label!r})".format(self=self))

    def __repr__(self):
        return "Wms.Location" + str(self)

    def quantity(self, goods_type, additional_states=None, at_datetime=None):
        """Return the full quantity in location for the given type.

        :param additional_states:
            Optionally, states of the Goods Avatar to take into account
            in addition to the ``present`` state.

            Hence, for ``additional_states=['past']``, we have the
            Goods Avatars that were already there and still are,
            as well as those that aren't there any more,
            and similarly for 'future'.
        :param at_datetime: take only into account Goods Avatar whose date
                            and time contains the specified value.

                            Mandatory if ``additional_states`` is specified.

        TODO: make recursive (not fully decided about the forest structure
        of locations)

        TODO: provide filtering according to Goods properties (should become
        special PostgreSQL JSON clauses)

        TODO PERF: for timestamp ranges, use GiST indexes and the @> operator.
        See the comprehensive answer to `that question
        <https://dba.stackexchange.com/questions/39589>`_ for an entry point.
        Let's get a DB with serious volume and datetimes first.
        """
        Goods = self.registry.Wms.Goods
        Avatar = Goods.Avatar
        query = Avatar.query(
            func.sum(Goods.quantity)).join(
                Avatar.goods).filter(
                    Goods.type == goods_type, Avatar.location == self)

        if additional_states is None:
            query = query.filter(Avatar.state == 'present')
        else:
            states = ('present',) + tuple(additional_states)
            query = query.filter(Avatar.state.in_(states))
            if at_datetime is None:
                # TODO precise exc or define infinites and apply them
                raise ValueError(
                    "Querying quantities with additional states {!r} requires "
                    "to specify the 'at_datetime' kwarg".format(
                        additional_states))

        if at_datetime is not None:
            query = query.filter(Avatar.dt_from <= at_datetime,
                                 or_(Avatar.dt_until.is_(None),
                                     Avatar.dt_until > at_datetime))
        res = query.one()[0]
        return 0 if res is None else res
