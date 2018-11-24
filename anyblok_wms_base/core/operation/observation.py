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
from anyblok.column import Text
from anyblok_postgres.column import Jsonb
from anyblok_wms_base.exceptions import (
    ObservationError,
    )

register = Declarations.register
Mixin = Declarations.Mixin
Operation = Declarations.Model.Wms.Operation

_missing = object()


@register(Operation)
class Observation(Mixin.WmsSingleInputOperation,
                  Mixin.WmsSingleOutcomeOperation,
                  Mixin.WmsInPlaceOperation,
                  Operation):
    """Operation to change PhysObj Properties.

    Besides being commonly associated with some measurement or assessment
    being done in reality, this Operation is the preferred way to alter the
    Properties of a physical object (PhysObj), in a traceable, reversible way.

    For now, only whole Property values are supported, i.e., for
    :class:`dict`-valued Properties, we can't observe the value of just a
    subkey.

    Observations support oblivion in the standard way, by reverting the
    Properties of the physical object to their prior values. This is
    consistent with the general rule that oblivion is to be used in cases
    where the database values themselves are irrelevant (for instance if the
    Observation was for the wrong physical object).

    On the other hand, reverting an Observation is semantically more
    complicated. See :meth:`plan_revert_single` for more details.
    """
    TYPE = 'wms_observation'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))
    """Primary key."""

    name = Text(nullable=True)
    """The name of the observation, to identity quickly an observation

    This field is optional and depends on the developer's needs.
    """

    observed_properties = Jsonb()
    """Result of the Observation.

    It is forbidden to fill this field for a planned Observation: this is
    thought to be contradictory with the idea of actually observing something.
    In the case of planned Observations, this field should be updated right
    before execution.

    TODO: rethink this, wouldn't it make sense actually to record some
    expected results, so that dependent Operations could be themselves planned
    ? This doesn't seem to be that useful though, since e.g., Assemblies
    can check different Properties during their different states. On the other
    hand, it could make sense in cases where the result is very often the same
    to prefill it.

    Another case would be for reversals: prefill the result.
    """

    previous_properties = Jsonb()
    """Used in particular during oblivion.

    This records key/value pairs of *direct* properties before execution of
    the Observation
    TODO and maybe reversal
    """

    required_properties = Jsonb()
    """List of Properties that must be present in :attr:`observed_properties`

    In other words, these are Properties the Observation must update.
    At execution time, the contents of :attr:`observed_properties` is examined
    and an error is raised if one of these properties is missing.
    """

    def after_insert(self):
        inp_av = self.input
        physobj = inp_av.obj
        state = self.state
        if state != 'done' and self.observed_properties is not None:
            raise ObservationError(
                self,
                "Forbidden to create a planned or just started "
                "Observation together with its results (this "
                "would mean one knows result in advance).")
        dt_exec = self.dt_execution

        inp_av.update(dt_until=dt_exec, state='past')
        physobj.Avatar.insert(
            obj=physobj,
            state='future' if state == 'planned' else 'present',
            outcome_of=self,
            location=self.input.location,
            dt_from=dt_exec,
            dt_until=None)

        if self.state == 'done':
            self.apply_properties()

    def apply_properties(self):
        """Save previous properties, then apply :attr:`observed_properties``

        The previous *direct* properties of the physical object get saved in
        :attr:`previous_properties`, then the
        key/value pairs of :attr:`observed_properties` are applied.

        In case an observed value is a new one, ie, there wasn't any *direct*
        key of that name before, it ends up simply to be absent from the
        :`previous_properties` dict (even if there was an inherited one).

        This allows for easy restoration of previous values in
        :meth:`obliviate_single`.
        """
        observed = self.observed_properties
        if observed is None:
            raise ObservationError(
                self, "Can't execute with no observed properties")
        required = self.required_properties
        if required:
            if not set(required).issubset(observed):
                raise ObservationError(
                    self, "observed_properties {observed!r} is missing "
                    "some of the required {required!r} ",
                    observed=set(observed), required=required)

        phobj = self.input.obj

        prev = {}
        existing = phobj.properties
        if existing:
            for k, v in observed.items():
                prev_val = existing.get(k, _missing)
                if prev_val is _missing:
                    continue
                prev[k] = prev_val

        self.previous_properties = prev
        phobj.update_properties(observed)

    def execute_planned(self):
        self.apply_properties()
        dt_exec = self.dt_execution
        self.input.update(dt_until=dt_exec, state='past')
        self.outcome.update(dt_from=dt_exec, state='present')

    def obliviate_single(self):
        """Restore the Properties as they were before execution.
        """
        phobj = self.input.obj
        for k in self.observed_properties:
            old_val = self.previous_properties.get(k, _missing)
            if old_val is _missing:
                del phobj.properties[k]
            else:
                phobj.properties[k] = old_val
        super(Observation, self).obliviate_single()

    def is_reversible(self):
        """Observations are always reversible.

        See :meth:`plan_revert_single` for a full discussion of this.
        """
        return True

    def plan_revert_single(self, dt_execution, follows=()):
        """Reverting an Observation is a no-op.

        For the time being, we find it sufficient to consider that
        Observations are really meant to find some information about the
        physical object (e.g a weight, a working condition). Therefore,
        reverting them doesn't make sense, while we don't want to consider
        them fully irreversible, so that a chain of Operations involving an
        Operation can still be reversed.

        The solution to this dilemma for the time being is that reverting
        an Observation does nothing. For instance, if an Observation follows
        some other Operation and has itself a follower,
        the outcome of the reversal of the
        follower is fed directly to the reversal of the previous operation.

        We may add more variants (reversal via a prefilled Observation etc.)
        in the future.
        """
        if not follows:
            # of course the Observation is not its own reversal, but
            # this tells reversals of upstream Operations to follow the
            # Observation
            return self
        # An Observation has at most a single follower, to make its
        # reversal trivial, it's enough to return the reversal of that
        # single follower
        return next(iter(follows))
