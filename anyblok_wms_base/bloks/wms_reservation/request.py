# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from contextlib import contextmanager

from sqlalchemy import CheckConstraint

from anyblok import Declarations
from anyblok.column import Integer
from anyblok.column import Boolean
from anyblok.relationship import Many2One
from anyblok_postgres.column import Jsonb

register = Declarations.register
Wms = Declarations.Model.Wms


@register(Wms.Reservation)
class Request:
    id = Integer(label="Identifier", primary_key=True)
    """Primary key.

    In this model, the ordering of ``id`` ordering is actually
    important (whereas on many others, it's a matter of habit to have
    a serial id): the smaller it is, the older the Request.

    Requests have to be reserved in order.

    Note that ``serial`` columns in PostgreSQL don't induce conflicts, as
    the sequence is evaluated out of transaction.
    """

    purpose = Jsonb()
    """Flexible field to describe what the reservations will be for.

    This is typically used by a planner, to produce an appropriate
    chain of Operations to fulfill that purpose.

    Example: in a simple sales system, we would record a sale order
    reference here, and the planner would then take the related Goods
    and issue (planned) Moves and Departures for their 'present' or
    'future' Avatars.
    """

    reserved = Boolean(nullable=False, default=False)
    """Indicates that all reservations are done.

    TODO: find a way to represent if the Request is partially done ?
    Some use-cases would require planning partial deliveries and the
    like in that case.
    """

    planned = Boolean(nullable=False, default=False)
    """Indicates that the planner has finished with that Request.

    It's better than deleting, because it allows to cancel all
    Operations, set this back to ``True``, and plan again.
    """

    txn_owned_reservations = set()
    """The set of Request ids whose current transaction owns reservations."""

    @classmethod
    @contextmanager
    def claim_reservations(cls, request_id=None):
        """Context manager to claim ownership over Request's reservations.

        This is meant for planners.

        By calling this, the current transaction becomes responsible
        for all Request's reservations, meaning that it has the
        liberty to issue any Operation affecting its Goods or their Avatars.

        :return: id of claimed Request
        :param int request_id:
           if not specified, the oldest not already claimed Request is
           claimed,  otherwise the one with the given id is. This is a
           numeric id so that the caller doesn't necessarily need to
           fetch all fields.

        This is safe with respect to concurrency: no other transaction
        can claim the same Request (guaranteed by a PostgreSQL lock).

        The session will forget about this Request as soon as one
        exits the ``with`` statement, and the underlying PG lock is
        released at the end of the transaction.

        TODO for now it's a context manager. I'd found it more
        elegant to tie it to the transaction, to get automatic
        release, without a ``with`` syntax, but that requires more
        digging into SQLAlchemy and Anyblok internals.

        TODO I think FOR UPDATE actually creates a new internal PG row
        (table bloat). Shall we switch to advisory locks (see PG doc) with an
        harcoded mapping to an integer ?
        If that's true, then performance-wise it's equivalent for us
        to set the txn id in some service column (but that would
        require inconditional cleanup, a complication)
        """
        query = cls.query('id')
        if request_id is not None:
            query = query.filter(cls.id == request_id)

        # issues a SELECT FOR UPDATE SKIP LOCKED (search
        #   'with_for_update' within
        #   http://docs.sqlalchemy.org/en/latest/core/selectable.html
        # also, noteworthy, SKIP LOCKED appeared within PostgreSQL 9.5
        #   (https://www.postgresql.org/docs/current/static/release-9-5.html)
        cols = query.with_for_update(skip_locked=True).order_by(
            cls.id).first()
        request_id = None if cols is None else cols[0]

        if request_id is not None:
            cls.txn_owned_reservations.add(request_id)
        yield request_id

        if request_id is not None:
            cls.txn_owned_reservations.discard(request_id)

    def is_txn_reservations_owner(self):
        """Tell if transaction is the owner of this Request's reservations.

        :return:
          ``True`` if the current transaction has claimed ownership,
          using the :meth:``claim_reservations`` method.
        """
        return self.id in self.txn_owned_reservations


@register(Wms.Reservation)
class RequestItem:

    id = Integer(label="Identifier", primary_key=True)
    """Primary key.

    Note that ``serial`` columns in PostgreSQL don't induce conflicts, as
    the sequence is evaluated out of transaction.
    """

    request = Many2One(model=Wms.Reservation.Request)

    goods_type = Many2One(model='Model.Wms.Goods.Type')

    quantity = Integer(nullable=False)

    properties = Jsonb()

    @classmethod
    def define_table_args(cls):
        return super(RequestItem, cls).define_table_args() + (
            CheckConstraint('quantity > 0', name='positive_qty'),
        )
