# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging
from datetime import datetime

from anyblok import Declarations
from anyblok.column import String
from anyblok.column import Selection
from anyblok.column import Integer
from anyblok.column import DateTime
from anyblok.relationship import Many2One

from anyblok_wms_base.utils import NonZero
from anyblok_wms_base.constants import OPERATION_STATES, OPERATION_TYPES
from anyblok_wms_base.exceptions import (
    OperationMissingInputsError,
    OperationInputsError,
    OperationInputWrongState,
    OperationError,
    OperationIrreversibleError,
    )

logger = logging.getLogger(__name__)
register = Declarations.register
Wms = Declarations.Model.Wms


NONZERO = NonZero()


@Declarations.register(Wms.Operation)
class HistoryInput:
    """Internal Model linking Operations with their inputs and together.

    The main purpose of this model is to represent the Direct Acyclic Graph
    (DAG) of Operations history, and its "weighing": the links to Operation
    inputs.

    Additionally, some things to keep track of for :ref:`cancel and oblivion
    <op_cancel_revert_obliviate>` are also stored there.
    """
    operation = Many2One(model='Model.Wms.Operation',
                         index=True,
                         primary_key=True,
                         foreign_key_options={'ondelete': 'cascade'})
    """The Operation we are interested in."""

    avatar = Many2One(model='Model.Wms.Goods.Avatar',
                      primary_key=True,
                      foreign_key_options={'ondelete': 'cascade'})
    """One of the inputs of the :attr:`operation`."""

    latest_previous_op = Many2One(model='Model.Wms.Operation',
                                  index=True)
    """The latest operation that affected :attr:`avatars` before :attr:`operation`.

    This is both the fundamental data structure suporting history (DAG)
    aspects of Operations, as is exposed in the :attr:`Operation.follows`
    and :attr:`Operation.followers` attributes and, on the other hand, the
    preservation of :attr:`reason
    <anyblok_wms_base.bloks.wms_core.goods.Avatar.reason>` for restore if
    needed, even after the :attr:`current operation <operation>` is done.
    """

    orig_dt_until = DateTime(label="Original dt_until of avatars")
    """Saving the original ``dt_until`` value of the :attr:`Avatar <avatar>`

    This is needed for :ref:`cancel and oblivion <op_cancel_revert_obliviate>`
    """


@register(Wms)
class Operation:
    """Base class for all Operations.

    .. warning:: downstream applications and libraries should never issue
                 :meth:`insert` for Operations in their main code, and must use
                 :meth:`create` instead. See the documention of :meth:`create`
                 for more about this.

    The Operation model encodes the common part of all precise operations,
    which themselves have dedicated models. This is implemented with the
    polymorphic features of SQLAlchemy and AnyBlok.

    The main purpose of this separation is to simplify the representation of
    operational history: Goods Avatars and Operations can be :class:`linked
    together <HistoryInput>` in full generality.

    Downstream applications and libraries can add columns on the present model
    to satisfy their auditing needs (some notion of "user" or "operator" comes
    to mind).
    """
    id = Integer(label="Identifier, shared with specific tables",
                 primary_key=True)
    """The primary key (serial integer)

    its value is equal to that of the concrete Operation Model.
    """

    # TODO enums ?
    type = Selection(label="Operation Type",
                     selections=OPERATION_TYPES,
                     nullable=False,
                     )
    """Polymorphic key to dispatch between the various Operation Models.

    As such keys are
    supposed to be unique among all polymorphic cases in the whole application,
    those defined by WMS Base are prefixed with ``wms_``.
    """
    state = Selection(label="State of operation",
                      selections=OPERATION_STATES,
                      nullable=False,
                      )
    """The current state (lifecycle step) of the Operation.

    See :ref:`op_states` for the meanings.
    """
    comment = String(label="Comment")
    """Free field.

    This is meant to store details of how it went, or motivation
    for the operation (downstream libraries implementing scheduling
    should better use columns rather than this field).

    .. note:: this shouldn't be ``wms-core`` responsibility, and hence should
              be simply removed.
    """

    def query_history_input(self):
        HI = self.registry.Wms.Operation.HistoryInput
        return HI.query().filter(HI.operation == self)

    @property
    def inputs(self):
        """The Avatars records the Operation is working on.

        This is a read-only pseudo field, initialized by :meth:`create()`.
        The backing data is actually stored in
        :class:`Model.Wms.Operation.HistoryInput <HistoryInput>`.
        """
        return [hi.avatar for hi in self.query_history_input().all()]

    @property
    def follows(self):
        """Immediate predecessors in the Operation history,

        These are the latest Operations that affected the
        :attr:`inputs` (and recorded themselves on them).

        There may be zero, one or more of them.

        Don't assume it'd be a list, it could as well be a set or
        tuple, or any iterable.

        Examples:

        * a move of a bottle of milk that follows the unpacking
          of a 6-pack, which itself follows a move from somewhere else
        * a parcel packing operation that follows exactly one move
          to the shipping area for each Goods to be packed.
          they themselves would follow more operations.
        * an :class:`Arrival <.arrival.Arrival>` typically doesn't
          follow anything (but might be due to some kind of purchase order).

        This is a read-only pseudo field, initialized by :meth:`create()`,
        The backing data is actually stored in
        :class:`Model.Wms.Operation.HistoryInput <HistoryInput>`.
        """
        return [hi.latest_previous_op
                for hi in self.query_history_input().all()]

    @property
    def followers(self):
        """The converse of :attr:`follows`

        These are the Operations that are directly after the curent one.
        There may be also 0, 1 or more of them.

        Don't assume it'd be a list, it could as well be a set or
        tuple, or any iterable.

        This is a read-only pseudo field, initialized by :meth:`create()`,
        The backing data is actually stored in
        :class:`Model.Wms.Operation.HistoryInput <HistoryInput>`.
        """
        HI = self.registry.Wms.Operation.HistoryInput
        return [hi.operation
                for hi in HI.query().filter(
                        HI.latest_previous_op == self).all()]

    dt_execution = DateTime(label="date and time of execution",
                            nullable=False)
    """Date and time of execution.

    For Operations in state ``done``, this represents the time at which the
    Operation has been completed, i.e., has reached that state.

    For Operations in states ``planned`` and ``started``,
    this represents the time at which the execution is supposed to complete.
    This has consequences on the :attr:`dt_from
    <anyblok_wms_base.bloks.wms_core.goods.Avatar.dt_from>` and :attr:`dt_until
    <anyblok_wms_base.bloks.wms_core.goods.Avatar.dt_until>` fields of
    the :ref:`Goods Avatars <goods_avatar>` affected by this Operation, to
    avoid summing up several :ref:`Avatars <goods_avatar>` of the same
    physical goods while :meth:`peeking at quantities in the future
    <anyblok_wms_base.bloks.wms_core.location.Location.quantity>`,
    but has no other strong meaning within
    ``wms-core``: if the end application does some serious time prediction,
    it can use it about freely. The actual execution can
    occur later at any time, be it sooner or later, as :meth:`execute`
    will in particular correct the value of this field, and its
    consequences on the affected :ref:`Avatars <goods_avatar>`.
    """

    dt_start = DateTime(label="date and time of start")
    """Date and time of start, if different than execution.

    For all Operations, if the value of this field is None, this means that
    the Operation is considered to be instantaneous.

    Overall, ``wms-core`` doesn't do much about this field other than recording
    it: end applications that perform does serious time predictions can use
    it about freely.

    .. note:: We will probably later on make use of this field in
              destructive Operations to update the :attr:`dt_until
              <anyblok_wms_base.bloks.wms_core.goods.Avatar.dt_until>` field
              of their inputs, meaning that they won't appear in
              present quantity queries anymore.

    For Operations in states ``done`` and ``started`` this represents the time
    at which the Operation has been started, i.e., has reached the ``started``
    state.

    For Operations in state ``planned``, this is as much theoretical as the
    field ``dt_execution`` is.
    """

    inputs_number = NONZERO
    """Number of :attr:`inputs` the Operation expects.

    This can be set by subclasses to impose a fixed number, as in
    :attr:`inputs_number <.on_goods.WmsSingleGoodsOperation>`

    In particular, purely creative subclasses must set this to 0
    """

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

    def link_inputs(self, inputs=None, clear=False, **fields):
        HI = self.registry.Wms.Operation.HistoryInput
        if clear:
            HI.query().filter(HI.operation == self).delete(
                synchronize_session='fetch')
        for avatar in inputs:
            HI.insert(avatar=avatar,
                      operation=self,
                      latest_previous_op=avatar.reason,
                      orig_dt_until=avatar.dt_until)

    @classmethod
    def create(cls, state='planned', inputs=None,
               dt_execution=None, dt_start=None, **fields):
        """Main method for creation of operations

        In contrast with :meth:`insert`, this class method performs
        some Wms specific logic,
        e.g, creation of Goods, but that's up to the specific subclasses.

        :param state:
           value of the :attr:`state` field right after creation. It has
           a strong influence on the consequences of the Operation:
           creating an Operation in the ``done`` state means executing it
           right away.

           Creating an Operation in the ``started`` state should
           make the relevant Goods and/or Avatar locked or destroyed right away
           (TODO not implemented)
        :param fields: remaining fields, to be forwarded to ``insert`` and
                       the various involved methods implemented in subclasses.
        :param dt_execution:
           value of the attr:`dt_execution` right at creation. If
           ``state==planned``, this is mandatory. Otherwise, it defaults to
           the current date and time (:meth:`datetime.now`)
        :return Operation: concrete instance of the appropriate Operation
                           subclass.

        In principle, downstream developers should never call :meth:`insert`.

        As this is Python, nothing really forbids them of doing so, but they
        must then exactly know what they are doing, much like issuing
        INSERT statements to the database).

        Keeping :meth:`insert` as in vanilla SQLAlchemy has the advantage of
        making them easily usable in
        ``wms_core`` internal implementation without side effects.

        On the other hand, downstream developers should feel free to
        :meth:`insert` and :meth:`update` in their unit or integration tests.
        The fact that they are inert should help reproduce weird situations
        (yes, the same could be achieved by forcing to use the Model class
        methods instead).
        """
        if dt_execution is None:
            if state == 'done':
                dt_execution = datetime.now()
            else:
                raise OperationError(
                    cls,
                    "Creation in state {state!r} requires the "
                    "'dt_execution' field (date and time when "
                    "it's supposed to be done).",
                    state=state)
        cls.check_create_conditions(
            state, dt_execution, inputs=inputs, **fields)
        inputs, fields_upd = cls.before_insert(state=state,
                                               inputs=inputs,
                                               dt_execution=dt_execution,
                                               dt_start=dt_start,
                                               **fields)
        if fields_upd is not None:
            fields.update(fields_upd)
        op = cls.insert(state=state, dt_execution=dt_execution, **fields)
        if inputs is not None:  # happens with creative Operations
            op.link_inputs(inputs)
        op.after_insert()
        return op

    @classmethod
    def before_insert(cls, inputs=None, **fields):
        return inputs, None

    def execute(self, dt_execution=None):
        """Execute the operation.

        :param datetime dt_execution:
           the time at which execution happens.
           This parameter is meant for tests, or for callers doing bulk
           execution. If omitted, it defaults to the current date
           and time (:meth:`datetime.now`)

        This is an idempotent call: if the operation is already done,
        nothing happens.
        """
        if self.state == 'done':
            return
        if dt_execution is None:
            dt_execution = datetime.now()
        self.dt_execution = dt_execution
        if self.dt_start is None:
            self.dt_start = dt_execution
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

    def is_reversible(self):
        """Tell whether the current operation can be in principle reverted.

        This does not check that actual conditions to plan a revert are met
        (which would need to plan reversals for all followers first),
        but only that, in principle, it is possible.

        :return: the answer
        :rtype: bool

        As there are many irreversible operations, and besides, reversibility
        has to be implemented for each subclass, the default implementation
        returns ``False``. Subclasses implementing reversibility have to
        override this.
        """
        return False

    def plan_revert(self, dt_execution=None):
        """Plan operations to revert the present one and its consequences.

        Like :meth:`cancel`, this method is recursive, but it applies only
        to operations that are in the 'done' state.

        It is expected that some operations can't be reverted, because they
        are destructive, and in that case an exception will be raised.

        For now, time handling is rather dumb, as it will plan
        all the operations at the same date and time (this Blok has to idea
        of operations lead times), but that shouldn't be a problem.

        :param datetime dt_execution:
           the time at which to plan the reversal operations.
           If not supplied, the current date and time will be used.

        :rtype: (Operation, list(Operation))
        :return: the operation reverting the present one, and
                 the list of initial operations to be executed to actually
                 start reversing the whole.
        """
        if dt_execution is None:
            dt_execution = datetime.now()
        if self.state != 'done':
            # TODO actually it'd be nice to cancel or update
            # planned operations (think of reverting a Move meant for
            # organisation, but keeping an Unpack that was scheduled
            # afterwards)
            raise OperationError(
                self,
                "Can't plan reversal of {op} because "
                "its state {op.state!r} is not 'done'", op=self)
        if not self.is_reversible():
            raise OperationIrreversibleError(self)

        logger.debug("Planning reversal of operation %r", self)

        exec_leafs = []
        followers_reverts = []
        for follower in self.followers:
            follower_revert, follower_exec_leafs = follower.plan_revert()
            self.registry.flush()
            followers_reverts.append(follower_revert)
            exec_leafs.extend(follower_exec_leafs)
        this_reversal = self.plan_revert_single(dt_execution,
                                                follows=followers_reverts)
        self.registry.flush()
        if not exec_leafs:
            exec_leafs.append(this_reversal)
        logger.info("Planned reversal of operation %r. "
                    "Execution starts with %r", self, exec_leafs)
        return this_reversal, exec_leafs

    def obliviate(self):
        """Totally forget about an executed Operation and all its consequences.

        This is intended for cases where an Operation has been recorded by
        mistake (bug or human error), but did not happen at all in reality.

        We chose the word "obliviate" because it has a stronger feeling that
        simply "forget" and also sound more specific.

        This is not to be confused with reversals, which try and create a
        chain of Operations to perform to revert the effect of some Operations.

        If one reverts a Move that has been done by mistake,
        that means one performs a Move back (takes some time, can go wrong).
        If one obliviates a Move, that means one
        acknowledges that the Move never happened: its mere existence in the
        database is itself the mistake.

        Also, some Operations cannot be reverted in reality, whereas oblivion
        in our sense have no effect on reality.

        This method will recursively obliviate all follow-ups of ``self``,
        before ``self`` itself.

        The implementation is for now a simple recursion, and hence can
        lead to :class:`RecursionError` on huge graphs.
        TODO rewrite using an accumulation logic rather than recursion.
        TODO it is also very much a duplication of :meth:`cancel`. The
        recursion logic itself should probably be factorized in a common
        method.

        TODO For the time being, the implementation insists on all Operations
        to be in the ``done`` state, but it should probably accept those
        that are in the ``planned`` state, and call :meth:`cancel` on them,
        maybe this could become an option if we can't decide.
        """
        if self.state != 'done':
            raise OperationError(
                self,
                "Can't obliviate {op} because its state {op.state!r} is not "
                "'obliviate'", op=self)
        logger.debug("Obliviating operation %r", self)

        # followers attribute value will mutate during the loop
        followers = tuple(self.followers)
        for follower in followers:
            follower.obliviate()
        self.obliviate_single()

        self.delete()
        # TODO check that we have a test for cascading on HistoryInput
        logger.info("Obliviated operation %r", self)

    def iter_inputs_original_values(self):
        """List inputs together with the original values stored in HistoryInput.

        Depending on the needs, it might be interesting to avoid
        actually fetching all those records.

        :return: a generator of pairs (goods, their original reasons,
        their original ``dt_until``)
        """
        # TODO simple n-column query instead
        return ((hi.avatar, hi.latest_previous_op, hi.orig_dt_until)
                for hi in self.query_history_input().all())

    def reset_inputs_original_values(self, state=None):
        """Reset all inputs to their original values; set state if passed.

        :param state: if not None, will be set on the inputs

        The original values are those currently held in
        :class:`Model.Wms.Operation.HistoryInput <HistoryInput>`.

        TODO PERF: it should be more efficient not to fetch the avatars and
        their records, but work directly on ids (and maybe do this in one pass
        with a clever UPDATE query).
        """
        for avatar, reason, dt_until in self.iter_inputs_original_values():
            if state is not None:
                avatar.state = state
            avatar.update(reason=reason, dt_until=dt_until)

    @classmethod
    def check_create_conditions(cls, state, dt_execution,
                                inputs=None, **kwargs):
        """Check that the conditions are met for the creation.

        This is done before calling ``insert()``.

        In this default implementation, we check

        - that the number of inputs is correct, by comparing
          with :attr:`inputs_number`, and
        - that they are all in the proper
          state for the wished :attr:`Operation state <state>`.

        Subclasses are welcome to override this, and will probably want to
        call it back, using ``super``.
        """
        expected = cls.inputs_number
        if not inputs:  # to include None
            if expected:
                raise OperationMissingInputsError(
                    cls,
                    "The 'inputs' keyword argument must be passed to the "
                    "create() method, and must not be empty "
                    "got {inputs})", inputs=inputs)
        elif len(inputs) != expected:
            raise OperationInputsError(
                cls,
                "Expecting exactly {exp} inputs, got {nb} of them: "
                "{inputs}", exp=expected, nb=len(inputs), inputs=inputs)

        if state == 'done' and inputs:
            for record in inputs:
                if record.state != 'present':
                    raise OperationInputWrongState(
                        cls, record, 'present',
                        prelude="Can't create in state 'done' "
                        "for inputs {inputs}",
                        inputs=inputs)

    @property
    def outcomes(self):
        """Return the outcomes of the present operation.

        Outcomes are the Goods Avatars that the current Operation produces,
        unless another Operation has been executed afterwards, becoming their
        reason.
        If no Operation is downstream, one can think of outcomes as the results
        of the current Operation.

        This default implementation considers that the :attr:`inputs`
        of the current Operation never are outcomes.

        This is a Python property, because it might become a field at some
        point.
        """
        Avatar = self.registry.Wms.Goods.Avatar
        # if already executed, might be the 'reason' for some Avatar
        # from self.inputs to be in 'past' state.
        return Avatar.query().filter(Avatar.reason == self,
                                     Avatar.state != 'past').all()

    def after_insert(self):
        """Perform specific logic after insert during creation process

        To be implemented in subclasses.
        """
        raise NotImplementedError  # pragma: no cover

    def check_execute_conditions(self):
        """Used during execution to check that the Operation is indeed doable.

        In this default implementation, we check that all the :attr:`inputs`
        are in the ``present`` state.

        Subclasses are welcome to override this, and will probably want to
        call it back, using ``super``.
        """
        if not self.inputs_number:
            # avoid a query with 0 results
            return

        for record in self.inputs:
            if record.state != 'present':
                raise OperationInputWrongState(
                    self, record, 'present',
                    prelude="Can't execute {operation}")

    def execute_planned(self):
        """Execute an operation that has been up to now in the 'planned' state.

        To be implemented in subclasses.

        This method does not have to care about the Operation state, which
        the base class has already checked.

        This method must correct the dates and times on the affected Avatars or
        more broadly of any consequences of the theoretical execution date
        and time that has been set during planning.
        For that purpose, it can rely on the value of the :attr:`dt_execution`
        field to be now the final one (can be sooner or later than expected).

        Normally, this method should not need either to perform any checks that
        the execution can, indeed, be done: such subclasses-specific
        tests are supposed to be done within :meth:`check_execute_conditions`.

        Downstream applications and libraries are
        not supposed to call this method: they should use :meth:`execute`,
        which takes care of all the above-mentioned preparations.
        """
        raise NotImplementedError  # pragma: no cover

    def delete_outcomes(self):
        """Delete outcomes of the current Operation and their Goods if needed

        This is used in the default implementations of :meth:`cancel_single`
        and :meth:`obliviate_single`.

        The Goods that the outcome Avatars were attached too get removed if
        they have no Avatar left. Typically that would be because they have been
        created along with the Avatars.
        """
        all_goods = set()
        for avatar in self.outcomes:
            all_goods.add(avatar.goods)
            avatar.delete()
        self.registry.flush()
        # TODO PERF probably more efficient in one query with GROUP BY + COUNT
        Avatar = self.registry.Wms.Goods.Avatar
        for goods in all_goods:
            if not Avatar.query().filter(Avatar.goods == goods).count():
                goods.delete()

    def cancel_single(self):
        """Cancel just the current operation.

        This method assumes that follow-up Operations have already been
        taken care of. It removes all planned consequences of the current one,
        but dos not delete it.

        The default implementation calls :meth:`reset_inputs_original_values`,
        then :meth:`delete_outcomes` (all outcomes should be in the `future`
        state).
        Subclasses should override this if there's more to be done.

        Downstream applications and libraries are
        not supposed to call this method: they should use :meth:`cancel`,
        which takes care of the necessary recursivity and the final deletion.
        """
        self.reset_inputs_original_values()
        self.registry.flush()
        self.delete_outcomes()

    def obliviate_single(self):
        """Oblivate just the current operation.

        This method assumes that follow-up Operations are already been
        taken care of. It removes all consequences of the current one,
        but does not delete it.

        The default implementation calls :meth:`reset_inputs_original_values`,
        then :meth:`delete_outcomes`.

        Subclasses should override this if there's more to be done.

        Downstream applications and libraries are
        not supposed to call this method: they should use :meth:`obliviate`,
        which takes care of the necessary recursivity and the final deletion.

        To be implemented in sublasses
        """
        self.reset_inputs_original_values(state='present')
        self.registry.flush()
        self.delete_outcomes()

    def plan_revert_single(self, dt_execution, follows=()):
        """Create a planned operation to revert the present one.

        This method assumes that reversals have already been issued for
        follow-up Operations, and takes them as input.

        :param datetime dt_execution: the date and time at which to plan
                                 the reversal operations.
        :param follows:
           the Operations that the reversal will have to follow. In other
           words, these are the reversals of ``self.followers`` (can be empty).
        :type follows: list(Operation)
        :return: the planned reversal
        :rtype: Operation

        Downstream applications and libraries are
        not supposed to call this method: they should use :meth:`plan_revert`,
        which takes care of the necessary recursivity.

        To be implemented in sublasses
        """
        raise NotImplementedError(
            "for %s" % self.__registry_name__)  # pragma: no cover
