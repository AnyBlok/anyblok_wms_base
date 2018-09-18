# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from sqlalchemy import CheckConstraint
from anyblok import Declarations
from anyblok.column import Integer
from anyblok.relationship import Many2One

register = Declarations.register
Wms = Declarations.Model.Wms


@register(Wms)
class Reservation:

    goods = Many2One(model=Wms.PhysObj, primary_key=True, index=True)
    quantity = Integer()
    """The quantity that this Reservation provides.

    If the PhysObj in the application have ``quantity`` field
    (see :ref:`improvement_no_quantities`), this is not necessarily its value
    within :attr:`goods`. Instead, it is the quantity within the
    :attr:`request_item` that the current Reservation provides.

    Use-case some PhysObj being sold either as packs of 10 or by
    the unit. If one wants to reserve 13 of them,
    it should be expressable as one pack of 10 and 3 units.
    Then maybe (depending on the needs), would it be actually
    smarter of the application to not issue an Unpack.
    """
    request_item = Many2One(model=Wms.Reservation.RequestItem,
                            index=True)

    @classmethod
    def define_table_args(cls):
        return super(Reservation, cls).define_table_args() + (
            CheckConstraint('quantity > 0', name='positive_qty'),
        )

    def is_transaction_owner(self):
        """Check that the current transaction is the owner of the reservation.
        """
        return self.request_item.request.is_txn_reservations_owner()

    def is_transaction_allowed(self, opcls, state, dt_execution,
                               inputs=None, **kwargs):
        """TODO add allowances, like a Move not far."""
        return self.is_transaction_owner()
