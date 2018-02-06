# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.

from sqlalchemy import func
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

    def quantity(self, goods_type, goods_state='present'):
        """Return the full quantity present in location for the given type.

        This doesn't take potential of Unpacks into account, so it's not
        readily suited for the question "do I have this in stock ?"

        TODO: make recursive (not fully decided about the forest structure
        of locations)
        TODO: provide filtering according to Goods properties (should become
        special PostgreSQL JSON clauses)
        TODO: add date filtering to peek into past, or do this on some
        other method
        """
        Goods = self.registry.Wms.Goods
        query = Goods.query(func.sum(Goods.quantity)).filter(
            Goods.type == goods_type, Goods.location == self)
        if goods_state == 'future':
            query = query.filter(Goods.state.in_(('future', 'present')))
        else:
            # this is where we'd be really happy with an Enum
            query = query.filter(Goods.state == goods_state)
        return query.one()[0]
