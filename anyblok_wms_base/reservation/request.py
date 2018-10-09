# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
import time
from contextlib import contextmanager

import sqlalchemy
from sqlalchemy import CheckConstraint
from sqlalchemy import func

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
    reference here, and the planner would then take the related PhysObj
    and issue (planned) Moves and Departures for their 'present' or
    'future' Avatars.
    """

    reserved = Boolean(nullable=False, default=False)
    """Indicates that all reservations are taken.

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
    def claim_reservations(cls, query=None, **filter_by):
        """Context manager to claim ownership over this Request's reservations.

        This is meant for planners and works on fully reserved Requests.
        Example::

           Request = registry.Wms.Reservation.Request
           with Request.claim_reservations() as req_id:
               request = Request.query().get(req_id)
               (...) read request.purpose, plan Operations (...)

        By calling this, the current transaction becomes responsible
        for all Request's reservations, meaning that it has the
        liberty to issue any Operation affecting its PhysObj or their Avatars.

        :return: id of claimed Request
        :param dict filter_by: direct filtering criteria to add to the
                               query, e.g, a planner looking for planning to
                               be done would pass ``planned=False``.
        :param query: if specified, is used to form the final SQL query,
                      instead of creating a new one.
                      The passed query must have the present model class in
                      its ``FROM`` clause and return only the ``id`` column
                      of the present model. The criteria of
                      ``filter_by`` are still applied if also provided.

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
        if query is None:
            query = cls.query('id')
        if filter_by is not None:
            query = query.filter_by(reserved=True, **filter_by)

        # issues a SELECT FOR UPDATE SKIP LOCKED (search
        #   'with_for_update' within
        #   http://docs.sqlalchemy.org/en/latest/core/selectable.html
        # also, noteworthy, SKIP LOCKED appeared within PostgreSQL 9.5
        #   (https://www.postgresql.org/docs/current/static/release-9-5.html)
        cols = query.with_for_update(skip_locked=True, of=cls).order_by(
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

    def reserve(self):
        """Try and perform reservation for all RequestItems.

        :return: ``True`` if all reservations are now taken
        :rtype: bool

        Should not fail if reservations are already done.
        """
        Item = self.registry.Wms.Reservation.RequestItem
        # could use map() and all(), but it's not recommended style
        # if there are strong side effects.
        all_reserved = True
        for item in Item.query().filter(Item.request == self).all():
            all_reserved = all_reserved and item.reserve()
        self.reserved = all_reserved
        return all_reserved

    @classmethod
    def lock_unreserved(cls, batch_size, query_filter=None, offset=0):
        """Take exclusivity over not yet reserved Requests

        This is used in :ref:`Reservers <arch_reserver>` implementations.

        :param int batch: maximum of reservations to lock at once.

        Since reservations have to be taken in order, this produces a hard
        error in case there's a conflicting database lock, instead of skipping
        them like :meth:`claim_reservations` does.

        This conflicts in particular locks taken with
        :meth`claim_reservations`, but in principle,
        only :ref:`reservers <arch_reserver>` should take locks
        over reservation Requests that are not reserved yet, and these should
        not run in concurrency (or in a very controlled way, using
        ``query_filter``).
        """
        query = cls.query().filter(cls.reserved.is_(False))
        if query_filter is not None:
            query = query_filter(query)
        query = query.with_for_update(nowait=True).order_by(cls.id)
        try:
            return query.limit(batch_size).offset(offset).all()
        except sqlalchemy.exc.OperationalError as op_err:
            cls.registry.rollback()
            raise cls.ReservationsLocked(op_err)

    class ReservationsLocked(RuntimeError):
        """Used to rewrap concurrency errors while taking locks."""
        def __init__(self, db_exc):
            self.db_exc = db_exc

    @classmethod
    def reserve_all(cls, batch_size=10, nb_attempts=5, retry_delay=1,
                    query_filter=None):
        """Try and perform all reservations for pending Requests.

        This walks all pending (:attr:`reserved` equal to ``False``)
        Requests that haven't been reserved from the oldest and locks
        them by batches of ``batch_size``.

        Reservation is attempted for each request, in order, meaning that
        each request will grab as much PhysObj as it can before the next one
        gets processed.

        :param int batch_size:
           number of pending Requests to grab at each iteration
        :param nb_attempts:
           number of attempts (in the face of conflicts) for each batch
        :param retry_delay:
           time to wait before retrying to grab a batch (hoping other
           transactions holding locks would have released them)
        :param query_filter:
           optional function to add filtering to the query used to grab the
           reservations. The caller can use this to implement controlled
           concurrency in the reservation process: several processes can
           focus on different Requests, as long as they don't compete for
           PhysObj to reserve.

        The transaction is committed for each batch, and that's essential
        for proper operation under concurrency.
        """
        skip = 0
        while True:
            # TODO log.info
            count = 1
            while True:
                try:
                    requests = cls.lock_unreserved(batch_size,
                                                   offset=skip,
                                                   query_filter=query_filter)
                except cls.ReservationsLocked:
                    # TODO log.warning
                    if count == nb_attempts:
                        raise
                    time.sleep(retry_delay)
                    count += 1
                else:
                    break
            if not requests:
                break

            for request in requests:
                if not request.reserve():
                    skip += 1
            cls.registry.commit()


@register(Wms.Reservation)
class RequestItem:

    id = Integer(label="Identifier", primary_key=True)
    """Primary key.

    Note that ``serial`` columns in PostgreSQL don't induce conflicts, as
    the sequence is evaluated out of transaction.
    """

    request = Many2One(model=Wms.Reservation.Request)

    goods_type = Many2One(model='Model.Wms.PhysObj.Type')

    quantity = Integer(nullable=False)

    properties = Jsonb()

    @classmethod
    def define_table_args(cls):
        return super(RequestItem, cls).define_table_args() + (
            CheckConstraint('quantity > 0', name='positive_qty'),
        )

    def lookup(self, quantity):
        """Try and find PhysObj matchin the specified conditions.

        :return: the matching PhysObj that were found and the quantity each
                 accounts for. The PhysObj may not be of the requested type.
                 What matters is how much of the requested quantity
                 each one represents.

        :rtype: list(int, :class:`PhysObj
                   <anyblok_wms_base/bloks/wms_core/goods.PhysObj`>)

        This method is where most business logic should lie.

        This default
        implementation does only equal matching on PhysObj Type and each
        property, and therefore is not able to return other PhysObj Type
        accounting for more than one of the wished.
        Downstream libraries and applications are welcome to override it.
        """
        Wms = self.registry.Wms
        PhysObj = Wms.PhysObj
        Reservation = Wms.Reservation
        Avatar = PhysObj.Avatar
        Props = PhysObj.Properties
        # TODO PERF this returns from the DB one PhysObj line per
        # Avatar, but SQLA reassembles them as exactly one (seen while
        # tracing the test_reserve_avatars_once() under pdb)
        # SELECT DISTINCT ON would be better
        # TODO provide ordering by Avatar state and/or dt_from
        query = PhysObj.query().join(Avatar.obj).outerjoin(
            Reservation, Reservation.physobj_id == PhysObj.id).filter(
                Reservation.physobj_id.is_(None),
                PhysObj.type == self.goods_type,
                Avatar.state.in_(('present', 'future')))
        if self.properties:
            props = self.properties.copy()
            query = query.join(PhysObj.properties)
            pfields = Props.fields_description()
            for p in set(props).intersection(pfields):
                query = query.filter(getattr(Props, p) == props.pop(p))
            if props:
                query = query.filter(Props.flexible.contains(props))
        return [(1, g) for g in query.limit(quantity).all()]

    def reserve(self):
        """Perform the wished reservations.

        :return bool: if the RequestItem is completely reserved.
                      TODO: shall we store it directly in DB ?
        """
        Reservation = self.registry.Wms.Reservation
        already = Reservation.query(func.sum(Reservation.quantity)).filter(
            Reservation.request_item_id == self.id).one()[0]
        if already is None:
            already = 0
        if already >= self.quantity:
            # its legit to be greater, think of reserving 2 packs of 10
            # to use 17. Maybe later, we'll unpack just one of them and update
            # the reservation to add just 7 of the Unpack outcomes.
            return True
        added = 0
        for quantity, goods in self.lookup(self.quantity - already):
            # TODO use a o2m ?
            Reservation.insert(goods=goods, quantity=quantity,
                               request_item=self)
            added += quantity
        return already + added >= self.quantity
