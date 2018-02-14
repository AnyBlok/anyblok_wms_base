# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging

from anyblok import Declarations
from anyblok.column import String
from anyblok.column import Selection
from anyblok.column import Integer
from anyblok.relationship import Many2Many

from anyblok_wms_base.constants import OPERATION_STATES, OPERATION_TYPES
from anyblok_wms_base.exceptions import (
    OperationCreateArgFollows,
    OperationError,
    )

logger = logging.getLogger(__name__)
register = Declarations.register
Model = Declarations.Model


@register(Model.Wms)
class Operation:
    """A stock operation.

    The Operation model encodes the common part of all precise operations,
    which themselves have dedicated models. This implemented through the
    polymorphic features of SQLAlchemy and AnyBlok.

    The main purpose of this separation is to simplify auditing purposes: the
    Goods model can bear a ``reason`` column, operations can be linked whatever
    their types are.

    Downstream applications and libraries can add columns on the present model
    to satisfy their auditing needs (some notion of "user" or "operator" comes
    to mind).

    Column semantics
    ----------------

    - id: is equal to the id of the concrete operations model
    - state: see mod:`constants`
    - comment: free field to store details of how it went, or motivation
               for the operation (downstream libraries implementing scheduling
               should better use columns rather than this field).
    - follows:
        the operations that are the direct reasons
        for the presence of Goods the present one is about.
        This is a Many2Many relationship because there might be
        several Goods involved in the operation, but for each of them,
        it'll be exactly one operation, namely the latest before
        the present one. In other words, operations history is a directed
        acyclic graph, whose edges are encoded by this Many2Many.

        This field can be empty in case of initial operations.

        Examples:

             + a move of a bottle of milk that follows the unpacking
               of a 6-pack, which itself follows a move from somewhere
               else
             + a parcel packing operation that follows exactly one move
               to the shipping area for each Goods to be packed.
               They themselves would follow more operations.
             + an Arrival typically doesn't follow anything (but might be due
               to some kind of purchase order).

    API
    ---
        Downstream applications and libraries should never call ``insert()``
        in their main code, and must use :meth:`create` instead.

        as this is Python, they still can, but that requires
        the developper to exactly know what they are doing, much like issuing
        INSERT statements in the console).

        Keeping ``insert()`` and ``update()`` behaviour as in vanilla
        SQLAlchemy has the advantage of making them easily usable in
        ``wms_core`` internal implementation without side effects.

        Downstream developers should feel free to use ``insert()`` and
        ``update()`` in their unit or integration tests. The fact that they
        are inert should help reproduce weird situations (yes, the same could
        be achieved by forcing the class in use).
    """
    id = Integer(label="Identifier, shared with specific tables",
                 primary_key=True)
    # TODO enums ?
    type = Selection(label="Operation Type",
                     selections=OPERATION_TYPES,
                     nullable=False,
                     )
    state = Selection(label="State of operation",
                      selections=OPERATION_STATES,
                      nullable=False,
                      )
    comment = String(label="Comment")
    follows = Many2Many(model='Model.Wms.Operation',
                        m2m_remote_columns='parent_id',
                        m2m_local_columns='child_id',
                        join_table='wms_operation_history',
                        label="Immediate preceding operations",
                        many2many="followers",
                        )

    @classmethod
    def define_mapper_args(cls):
        mapper_args = super(Operation, cls).define_mapper_args()
        if cls.__registry_name__ == 'Model.Wms.Operation':
            mapper_args.update({
                'polymorphic_identity': 'operation',
                'polymorphic_on': cls.type,
            })
        else:
            mapper_args.update({
                'polymorphic_identity': cls.TYPE,
            })

        return mapper_args

    def __repr__(self):
        return ("{model_name}(id={self.id}, state={self.state!r}, "
                "{specific})").format(self=self,
                                      model_name=self.__registry_name__,
                                      specific=self.specific_repr())

    __str__ = __repr__

    @classmethod
    def forbid_follows_in_create(cls, follows, kwargs):
        if follows is not None:
            raise OperationCreateArgFollows(cls, kwargs)

    @classmethod
    def create(cls, state='planned', follows=None, **kwargs):
        """Main method for creation of operations

        In contrast with ``insert()``, it performs some Wms specific logic,
        e.g, creation of Goods, but that's up to the specific subclasses.
        """
        cls.forbid_follows_in_create(follows, kwargs)
        cls.check_create_conditions(state, **kwargs)
        follows = cls.find_parent_operations(**kwargs)
        op = cls.insert(state=state, **kwargs)
        op.follows.extend(follows)
        op.after_insert()
        return op

    def execute(self):
        """Execute the operation.

        This is an idempotent call: if the operation is already done,
        nothing happens.
        """
        if self.state == 'done':
            return
        self.check_execute_conditions()
        self.execute_planned()
        self.state = 'done'

    def cancel(self):
        """Cancel a planned operation and all its consequences.

        This method will recursively cancel all follow-ups of ``self``, before
        cancelling ``self`` itself.

        The implementation is for now a simple recursion, and hence can
        lead to :class:`RecursionError` on huge graphs.
        TODO rewrite using an accumulation logic rather than recursion.
        """
        if self.state != 'planned':
            raise OperationError(
                self,
                "Can't cancel {op} because its state {op.state!r} is not "
                "'planned'", op=self)
        logger.debug("Cancelling operation %r", self)

        # followers attribute value will mutate during the loop
        followers = tuple(self.followers)
        for follower in followers:
            follower.cancel()
        self.cancel_single()
        self.follows.clear()
        self.delete()
        logger.info("Cancelled operation %r", self)

    def plan_revert(self):
        """Plan operations to revert the present one and its consequences.

        Like :meth:`cancel`, this method is recursive, but it applies only
        to operations that are in the 'done' state.

        It is expected that some operations can't be reverted, because they
        are destructive, and in that case an exception will be raised.

        :return: the operation reverting the present one, and
                 the list of initial operations to be executed to actually
                 start reversing the whole.
        """
        if self.state != 'done':
            # TODO actually it'd be nice to cancel or update
            # planned operations (think of reverting a Move meant for
            # organisation, but keeping an Unpack that was scheduled
            # afterwards)
            raise OperationError(
                self,
                "Can't plan reversal of {op} because "
                "its state {op.state!r} is not 'done'", op=self)
        logger.debug("Planning reversal of operation %r", self)

        exec_leafs = []
        followers_reverts = []
        for follower in self.followers:
            follower_revert, follower_exec_leafs = follower.plan_revert()
            self.registry.flush()
            followers_reverts.append(follower_revert)
            exec_leafs.extend(follower_exec_leafs)
        this_reversal = self.plan_revert_single(follows=followers_reverts)
        self.registry.flush()
        if not exec_leafs:
            exec_leafs.append(this_reversal)
        logger.info("Planned reversal of operation %r. "
                    "Execution starts with %r", self, exec_leafs)
        return this_reversal, exec_leafs

    @classmethod
    def check_create_conditions(cls, state, **kwargs):
        """Used during creation to check that the Operation is indeed doable.

        The given state obviously plays a role, and this pre insertion check
        can spare us some costly operations.

        To be implemented in subclasses, by raising exceptions if something's
        wrong.
        """
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def find_parent_operations(cls, **kwargs):
        """Return the list or tuple of operations that this one follows

        To be implemented in subclasses.
        """
        raise NotImplementedError  # pragma: no cover

    def after_insert(self):
        """Perform specific logic after insert during creation process

        To be implemented in subclasses.
        """
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def check_execute_conditions(cls, **kwargs):
        """Used during execution to check that the Operation is indeed doable.

        To be implemented in subclasses, by raising an exception if something's
        wrong.
        """
        raise NotImplementedError  # pragma: no cover

    def execute_planned(self):
        """Execute an operation that's up to now in the 'planned' state.

        This method does not have to care about the Operation state.

        To be implemented in subclasses.
        """
        raise NotImplementedError  # pragma: no cover

    def cancel_single(self):
        """Cancel just the current operation.

        This method assumes that follow-up operations are already been
        taken care of. It removes all planned consequences of the operation,
        without deleting the operation itself.

        Downstream applications and libraries are
        not supposed to call this method: they should use :meth:`cancel`,
        which takes care of the necessary recursivity and the final deletion.

        To be implemented in sublasses
        """
        raise NotImplementedError(
            "for %s" % self.__registry_name__)  # pragma: no cover

    def plan_revert_single(self):
        """Create a planned operation to revert the present one.

        This method assumes that follow-up operations have already been taken
        care of.

        Downstream applications and libraries are
        not supposed to call this method: they should use :meth:`plan_revert`,
        which takes care of the necessary recursivity.

        To be implemented in sublasses
        """
        raise NotImplementedError(
            "for %s" % self.__registry_name__)  # pragma: no cover
