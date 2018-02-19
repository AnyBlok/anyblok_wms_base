# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.

from anyblok import Declarations
from anyblok.column import Integer
from anyblok.relationship import Many2One
from anyblok_wms_base.exceptions import OperationError


register = Declarations.register
Operation = Declarations.Model.Wms.Operation
SingleGoodsSplitter = Declarations.Mixin.WmsSingleGoodsSplitterOperation


@register(Operation)
class Move(SingleGoodsSplitter, Operation):
    """A stock move
    """
    TYPE = 'wms_move'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))
    destination = Many2One(model='Model.Wms.Location',
                           nullable=False)
    origin = Many2One(model='Model.Wms.Location',
                      label="Set during execution, for cancel/revert/rollback")

    def specific_repr(self):
        return ("goods={self.goods!r}, "
                "destination={self.destination!r}").format(self=self)

    @classmethod
    def check_create_conditions(cls, state, origin=None, **kwargs):
        if origin is not None:
            raise OperationError(cls, "The 'origin' field must *not* "
                                 "be passed to the create() method")
        super(Move, cls).check_create_conditions(state, **kwargs)

    def after_insert(self):
        goods = self.goods
        self.origin = self.goods.location
        if self.partial or self.state == 'done':
            self.registry.flush()
            goods.update(location=self.destination, reason=self)
        else:
            fields = dict(reason=self,
                          state='future',
                          type=goods.type,
                          code=goods.code,
                          properties=goods.properties)
            Goods = self.registry.Wms.Goods
            Goods.insert(location=self.destination,
                         quantity=self.quantity,
                         **fields)
            Goods.insert(location=goods.location,
                         quantity=-self.quantity,
                         **fields)

    def execute_planned_after_split(self):
        goods = self.goods
        if self.partial:
            # not done by the split, because goods' reason is already the Move
            goods.state = 'present'
            return

        Goods = self.registry.Wms.Goods
        query = Goods.query().filter(Goods.reason == self)
        query.filter(Goods.quantity < 0).delete(synchronize_session='fetch')

        after_move = query.one()
        after_move.state = 'present'
        self.registry.flush()
        self.goods = after_move
        self.registry.flush()
        # TODO it'd be maybe nicer if Moves could guarantee continuity of
        # the Goods record, but then that'd mean updating all the operations
        # that refer to after_move, and we have no generic way of finding
        # them at the time being.
        # One idea would be to traverse the DAG of
        # follow-ups and change all of them if they have a goods field whose
        # value is or contains  that move's goods.
        # Another idea would be to introspect
        # dynamically all Operation classes having a goods field (m2o or m2m)
        # None of this would be in favor of privileging operator's reactivity,
        # by careful preparation of ops.

        # can't goods.delete() because another op might refer it
        # TODO dates
        goods.state = 'past'
        goods.reason = self

    def cancel_single(self):
        goods = self.goods
        if self.partial:
            split = self.follows[0]
            goods.reason = split
        goods.location = self.origin
        self.registry.flush()
        Goods = self.registry.Wms.Goods
        Goods.query().filter(Goods.reason == self).delete(
            synchronize_session='fetch')

    def obliviate_single(self):
        self.goods.update(location=self.origin,
                          reason=self.follows[0],
                          state='present')
        self.registry.flush()
        Goods = self.registry.Wms.Goods
        Goods.query().filter(Goods.reason == self).delete(
            synchronize_session='fetch')

    def is_reversible(self):
        """Moves are always reversible.

        See :class:`Operation` for what this exactly means.
        """
        return True

    def plan_revert_single(self, follows=()):
        if not follows:
            # reversal of an end-of-chain move
            reason = self
        else:
            # A move has at most a single follower, hence
            # its reversal follows at most one operation, whose
            # outcome is one Goods record
            reason = follows[0]
        Goods = self.registry.Wms.Goods
        # TODO introduce an outcome() generic API for all operations ?
        goods = Goods.query().filter(Goods.reason == reason,
                                     Goods.quantity > 0).one()
        return self.create(goods=goods,
                           quantity=self.quantity,
                           destination=self.origin,
                           state='planned')
