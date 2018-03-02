# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok import Declarations
from anyblok.relationship import Many2One

register = Declarations.register
Wms = Declarations.Model.Wms


@register(Wms)
class Reservation:

    goods = Many2One(model=Wms.Goods, primary_key=True, index=True)
    request_item = Many2One(model=Wms.Reservation.RequestItem,
                            index=True)

    def is_transaction_owner(self):
        """Check that the current transaction is the owner of the reservation.
        """
        return self.request_item.request.is_txn_reservations_owner()

    def is_transaction_allowed(self, opcls, state, dt_execution,
                               inputs=None, **kwargs):
        """TODO add allowances, like a Move not far."""
        return self.is_transaction_owner()
