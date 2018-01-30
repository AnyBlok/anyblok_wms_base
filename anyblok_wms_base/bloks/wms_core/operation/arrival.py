# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.

from anyblok import Declarations
from anyblok.column import Decimal
from anyblok.column import Integer
from anyblok.relationship import Many2One

register = Declarations.register
Operation = Declarations.Model.Wms.Operation


@register(Operation)
class Arrival(Operation):
    """Operation to describe physical arrival of goods in some location.

    This does not encompass all "creations" of goods : only those that
    come in real life from the outside.

    Open functional question : do we need properties on arrivals ?
    If yes, what would they describe in case of a planned arrival
    only some subset of expected properties ? And then once the arrival
    operation is done, are they the actual properties or the original
    expected ones ? Do we want automatic forwarding of properties to goods ?
    If yes that means that properties of Goods are expected to diverge
    from reality and their checking is not part of the Arrival operation.
    Same question holds actually for quantity.
    """
    TYPE = 'wms_arrival'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))
    goods_type = Many2One(model='Model.Wms.Goods.Type')
    location = Many2One(model='Model.Wms.Location')
    quantity = Decimal(label="Quantity")  # TODO non negativity constraint
