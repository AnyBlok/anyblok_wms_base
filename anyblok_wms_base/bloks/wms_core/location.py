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

    def __repr__(self):
        return ("Wms.Location(id={self.id}, code={self.code!r}, "
                "label={self.label!r})".format(self=self))

    def quantity(self, goods_type, goods_state='present', at_datetime=None):
        """Return the full quantity in location for the given type.

        :param goods_state:
            if not 'present', then ``at_datetime`` is
            mandatory, the query is filtered for this
            date and time, and the query includes the Goods
            with state == 'present' anyway.

            #TODO renaming as ``with_state`` or similar would be clearer.

            Hence, for ``goods_state='past'``, we have the
            Goods that were already there and still are,
            as well as those that aren't there any more,
            and similarly for the future.

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
        query = Goods.query(func.sum(Goods.quantity)).filter(
            Goods.type == goods_type, Goods.location == self)
        if goods_state == 'present':
            query = query.filter(Goods.state == goods_state)
        else:
            if at_datetime is None:
                # TODO precise exc or define infinites and apply them
                raise ValueError(
                    "Querying quantities in state {!r} requires "
                    "to specify the 'at_datetime' kwarg".format(goods_state))
            query = query.filter(Goods.state.in_((goods_state, 'present')),
                                 Goods.dt_from <= at_datetime,
                                 or_(Goods.dt_until.is_(None),
                                     Goods.dt_until > at_datetime))
        res = query.one()[0]
        return 0 if res is None else res
