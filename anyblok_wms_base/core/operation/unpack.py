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

from anyblok_wms_base.constants import CONTENTS_PROPERTY
from anyblok_wms_base.exceptions import OperationInputsError

register = Declarations.register
Mixin = Declarations.Mixin
Operation = Declarations.Model.Wms.Operation


@register(Operation)
class Unpack(Mixin.WmsSingleInputOperation,
             Mixin.WmsInPlaceOperation,
             Operation):
    """Unpacking some goods, creating new PhysObj and Avatar records.

    This is a destructive Operation, in the usual mild sense: once it's done,
    the input PhysObj Avatars is in the ``past`` state, and their underlying
    PhysObj have no new Avatars.

    It is conditionally reversible through appropriate Assembly Operations.

    Which PhysObj will get created and which Properties they will bear is
    specified in the ``unpack`` behaviour of the Type of the PhysObj being
    unpacked, together with their ``contents`` optional Properties.
    See :meth:`get_outcome_specs` and :meth:`forward_props` for details
    about these and how to achieve the wished functionality.

    Unpacks happen in place: the newly created Avatar appear in the
    location where the input was. It is thus the caller's responsibility to
    prepend moves to unpacking areas, and/or append moves to final
    destinations.
    """
    TYPE = 'wms_unpack'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))

    @classmethod
    def check_create_conditions(cls, state, dt_execution,
                                inputs=None, quantity=None, **kwargs):
        # TODO quantity is now irrelevant in wms-core
        super(Unpack, cls).check_create_conditions(
            state, dt_execution, inputs=inputs,
            quantity=quantity,
            **kwargs)

        goods_type = inputs[0].obj.type
        if 'unpack' not in goods_type.behaviours:
            raise OperationInputsError(
                cls,
                "Can't create an Unpack for {inputs} "
                "because their type {type} doesn't have the 'unpack' "
                "behaviour", inputs=inputs, type=goods_type)

    def execute_planned(self):
        packs = self.input
        # TODO PERF direct update query would probably be faster
        for outcome in self.outcomes:
            outcome.state = 'present'
        packs.update(state='past')

    def create_unpacked_goods(self, fields, spec):
        """Create PhysObj record according to given specification.

        This singled out method is meant for easy subclassing (see, e.g,
        in :ref:`wms-quantity Blok <blok_wms_quantity>`).

        :param fields: pre-baked fields, prepared by the base class. In the
                       current implementation, they are fully derived from
                       ``spec``, hence one may think of them as redundant,
                       but the point is that they are outside the
                       responsibility of this method.
        :param spec: specification for these PhysObj, should be used minimally
                     in subclasses, typically for quantity related adjustments.
                     Also, if the special ``local_physobj_ids`` is provided,
                     this method should attempt to reuse the PhysObj record
                     with that ``id`` (interplay with quantity might depend
                     on the implementation).
        :return: the list of created PhysObj records. In ``wms-core``, there
                 will be as many as the wished quantity, but in
                 ``wms-quantity``, this maybe a single record bearing the
                 total quantity.
        """
        PhysObj = self.registry.Wms.PhysObj
        existing_ids = spec.get('local_physobj_ids')
        target_qty = spec['quantity']
        if existing_ids is not None:
            if len(existing_ids) != target_qty:
                raise OperationInputsError(
                    self,
                    "final outcome specification {spec!r} has "
                    "'local_physobj_ids' parameter, but they don't provide "
                    "the wished total quantity {target_qty} "
                    "Detailed input: {inputs[0]!r}",
                    spec=spec, target_qty=target_qty)
            return [PhysObj.query().get(eid) for eid in existing_ids]
        return [PhysObj.insert(**fields) for _ in range(spec['quantity'])]

    def after_insert(self):
        PhysObj = self.registry.Wms.PhysObj
        PhysObjType = PhysObj.Type
        packs = self.input
        dt_execution = self.dt_execution
        spec = self.get_outcome_specs()
        type_codes = set(outcome['type'] for outcome in spec)
        outcome_types = {gt.code: gt
                         for gt in (PhysObjType.query()
                                    .filter(PhysObjType.code.in_(type_codes))
                                    .all())}

        outcome_state = 'present' if self.state == 'done' else 'future'
        if self.state == 'done':
            packs.update(state='past')
        for outcome_spec in spec:
            self.create_outcomes_for_spec(
                outcome_types, outcome_spec, outcome_state)
        packs.dt_until = dt_execution

    def create_outcomes_for_spec(self, types_cache, spec, outcome_state):
        PhysObj = self.registry.Wms.PhysObj
        # TODO what would be *really* neat would be to be able
        # to recognize the goods after a chain of pack/unpack
        goods_fields = dict(type=types_cache[spec['type']])
        packs = self.input
        clone = spec.get('forward_properties') == 'clone'
        if clone:
            goods_fields['properties'] = packs.obj.properties
        for physobj in self.create_unpacked_goods(goods_fields,
                                                  spec):
            PhysObj.Avatar.insert(obj=physobj,
                                  location=packs.location,
                                  outcome_of=self,
                                  dt_from=self.dt_execution,
                                  dt_until=packs.dt_until,
                                  state=outcome_state)
            if not clone:
                physobj.update_properties(self.outcome_props_update(spec))

    @classmethod
    def plan_for_outcomes(cls, inputs, outcomes, dt_execution=None):
        """Create a planned Unpack of which some outcomes are already given.

        This is useful for planning refinements, in cases the given ``future``
        outcomes already exist in the database, typically because they are
        from Arrivals that are in the :meth:`process of being superseded
        <anyblok_wms_base.core.operation.arrival.Arrival.refine_with_trailing_unpack>`

        :param inputs: should be made of only one element, an Avatar of the
                       physical object to be unpacked, yet it's convenient
                       to get it as an iterable (also for the caller).
        :param outcomes: candidate Avatars to reinterpret as outcomes of the
                         newly created Unpack. It is possible that the Unpack
                         produces some extra ones, and conversely that some
                         of them are not produced by the Unpack.
        :returns: a pair made of

                  - the created Unpack
                  - the sublist of ``outcomes`` that have been attached.

        This method ensures that the newly created Unpack instance produces
        at least the same properties as already present on the given outcomes,
        and actually uses the properties as a match criteria to perform the
        attachments.
        It is on the other hand perfectly acceptable that the Unpack adds
        more properties, for instance because they were previously unplannable
        or irrelevant for the planning (use cases: serial and batch numbers,
        expiry dates...)
        """  # noqa (unbreakable Sphinx crossref)
        if dt_execution is None:
            # TODO improve using outcomes dt_from
            dt_execution = max(inp.dt_from for inp in inputs)

        cls.check_create_conditions('planned', dt_execution, inputs)
        unpack = cls.insert(state='planned', dt_execution=dt_execution)
        unpack.link_inputs(inputs)
        input_obj = next(iter(inputs)).obj

        to_match = set(outcomes)
        attached = []
        PhysObj = cls.registry.Wms.PhysObj
        POT = PhysObj.Type
        # TODO PERF this has quadratic complexity.
        # I suppose it's ok because outcomes shoudl not be too big,
        # but it could be improved by presorting specs and outcomes
        # TODO it's quite possible that some of the outcome can't be matched
        # because the spec item that would match it has already been used
        # to match one with less properties
        code_to_type = {}
        for spec in unpack.get_outcome_specs():
            code = spec['type']
            stype = code_to_type.get(code)
            if stype is None:
                stype = POT.query().filter_by(code=code).one()
                code_to_type[code] = stype
            for i in range(spec['quantity']):
                # breaking out of this loops means we already match as much
                # as possible
                for candidate in to_match:
                    # breaking out of this loop signals a match
                    cand_obj = candidate.obj
                    if cand_obj.type != stype:
                        continue
                    sprops = spec['forward_properties']
                    if cand_obj.properties is None:
                        # easy case: no properties to match, only new ones
                        # to create
                        if sprops == 'clone':
                            cand_obj.properties = input_obj.properties
                        else:
                            cand_obj.update_properties(
                                unpack.outcome_props_update(spec))
                        break
                    # else, we check if candidate's properties are a subdict
                    # of what the Unpack would give rise to
                    props_from_spec = unpack.outcome_props_update(spec)
                    cand_props = cand_obj.properties.as_dict()
                    if all(props_from_spec.get(k) == v
                           for k, v in cand_props.items()):
                        cand_obj.update_properties(props_from_spec)
                        break
                else:
                    break
                to_match.remove(candidate)
                attached.append(candidate)
                candidate.update(outcome_of=unpack,
                                 dt_from=dt_execution)
            else:
                continue  # next spec
            spec['quantity'] -= i
            unpack.create_outcomes_for_spec(code_to_type, spec, 'future')

        return unpack, attached

    def outcome_props_update(self, spec):
        """Handle the properties for a given outcome (PhysObj record)

        This is actually a bit more that just forwarding.

        :param dict spec: the relevant specification for this outcome, as
                          produced by :meth:`get_outcome_specs` (see below
                          for the contents).
        :param outcome: the just created PhysObj instance
        :return: the properties to update, as a :class:`dict`

        *Specification contents*

        * ``properties``:
            A direct mapping of properties to set on the outcome. These have
            the lowest precedence, meaning that they will
            be overridden by properties forwarded from ``self.input``.

            Also, if spec has the ``local_physobj_id`` key, ``properties`` is
            ignored. The rationale for this is that normally, there are no
            present or future Avatar for these PhysObj, and therefore the
            Properties of outcome should not have diverged from the contents
            of ``properties`` since the spec (which must itself not come from
            the behaviour, but instead from ``contents``) has been
            created (typically by an Assembly).
        * ``required_properties``:
            list (or iterable) of properties that are required on
            ``self.input``. If one is missing, then
            :class:`OperationInputsError` gets raised.
            ``forward_properties``.
        * ``forward_properties``:
            list (or iterable) of properties to copy if present from
            ``self.input`` to ``outcome``.

        Required properties aren't automatically forwarded, so that it's
        possible to require one for checking purposes without polluting the
        Properties of ``outcome``. To forward and require a property, it has
        thus to be in both lists.
        """
        props_upd = {}
        direct_props = spec.get('properties')
        if direct_props is not None and 'local_physobj_ids' not in spec:
            props_upd.update(direct_props)
        packs = self.input.obj
        fwd_props = spec.get('forward_properties', ())
        req_props = spec.get('required_properties')

        if req_props and not packs.properties:
            raise OperationInputsError(
                self,
                "Packs {inputs[0]} have no properties, yet their type {type} "
                "requires these for Unpack operation: {req_props}",
                type=packs.type, req_props=req_props)
        if not fwd_props:
            return props_upd

        for pname in fwd_props:
            pvalue = packs.get_property(pname)
            if pvalue is None:
                if pname not in req_props:
                    continue
                raise OperationInputsError(
                    self,
                    "Packs {inputs[0]} lacks the property {prop}"
                    "required by their type for Unpack operation",
                    prop=pname)
            props_upd[pname] = pvalue
        return props_upd

    def get_outcome_specs(self):
        """Produce a complete specification for outcomes and their properties.

        In what follows "the behaviour" means the value associated with the
        ``unpack`` key in the PhysObj Type :attr:`behaviours
        <anyblok_wms_base.core.physobj.Type.behaviours>`.

        Unless ``uniform_outcomes`` is set to ``True`` in the behaviour,
        the outcomes of the Unpack are obtained by merging those defined in
        the behaviour (under the ``outcomes`` key) and in the
        packs (``self.input``) ``contents`` Property.

        This accomodates various use cases:

        - fixed outcomes:
            a 6-pack of orange juice bottles gets unpacked as 6 bottles
        - fully variable outcomes:
            a parcel with described contents
        - variable outcomes:
            a packaging with parts always present and some varying.

        The properties on outcomes are set from those of ``self.input``
        according to the ``forward_properties`` and ``required_properties``
        of the outcomes, unless again if ``uniform_outcomes`` is set to
        ``True``, in which case the properties of the packs (``self.input``)
        aren't even read, but simply
        cloned (referenced again) in the outcomes. This should be better
        for performance in high volume operation.
        The same can be achieved on a given outcome by specifying the
        special ``'clone'`` value for ``forward_properties``.

        Otherwise, the ``forward_properties`` and ``required_properties``
        unpack behaviour from the PhysObj Type of the packs (``self.input``)
        are merged with those of the outcomes, so that, for instance
        ``forward_properties`` have three key/value sources:

        - at toplevel of the behaviour (``uniform_outcomes=True``)
        - in each outcome of the behaviour (``outcomes`` key)
        - in each outcome of the PhysObj record (``contents`` property)

        Here's a use-case: imagine the some purchase order reference is
        tracked as property ``po_ref`` (could be important for accounting).

        A PhysObj Type representing an incoming package holding various PhysObj
        could specify that ``po_ref`` must be forwarded upon Unpack in all
        cases. For instance, a PhysObj record with that type could then
        specify that its outcomes are a phone with a given ``color``
        property (to be forwarded upon Unpack)
        and a power adapter (whose colour is not tracked).
        Both the phone and the power adapter would get the ``po_ref``
        forwarded, with no need to specify it on each in the incoming pack
        properties.

        TODO DOC move a lot to global doc
        """
        # TODO PERF playing safe by performing a copy, in order not
        # to propagate mutability to the DB. Not sure how much of it
        # is necessary.
        packs = self.input
        goods_type = packs.obj.type
        behaviour = goods_type.get_behaviour('unpack')
        specs = behaviour.get('outcomes', [])[:]
        if behaviour.get('uniform_outcomes', False):
            for outcome in specs:
                outcome['forward_properties'] = 'clone'
            return specs

        specific_outcomes = packs.get_property(CONTENTS_PROPERTY, ())
        specs.extend(specific_outcomes)
        if not specs:
            raise OperationInputsError(
                self,
                "unpacking {inputs[0]} yields no outcomes. "
                "Type {type} 'unpack' behaviour: {behaviour}, "
                "specific outcomes from PhysObj properties: "
                "{specific}",
                type=goods_type, behaviour=behaviour,
                specific=specific_outcomes)

        global_fwd = behaviour.get('forward_properties', ())
        global_req = behaviour.get('required_properties', ())
        for outcome in specs:
            if outcome.get('forward_properties') == 'clone':
                continue
            outcome.setdefault('forward_properties', []).extend(global_fwd)
            outcome.setdefault('required_properties', []).extend(global_req)
        return specs

    def cancel_single(self):
        """Remove the newly created PhysObj, not only their Avatars."""
        self.reset_inputs_original_values()
        self.registry.flush()
        all_goods = set()
        # TODO PERF in two queries using RETURNING, or be braver and
        # make the avatars cascade
        for avatar in self.outcomes:
            all_goods.add(avatar.obj)
            avatar.delete()
        for goods in all_goods:
            goods.delete()

    def reverse_assembly_name(self):
        """Return the name of Assembly that can revert this Unpack."""
        behaviour = self.input.obj.type.get_behaviour('unpack')
        default = 'pack'
        if behaviour is None:
            return default  # probably not useful, but that's consistent
        return behaviour.get('reverse_assembly', default)

    def is_reversible(self):
        """Unpack can be reversed by an Assembly.

        The exact criterion is that Unpack can be reversed, if there exists
        an :class:`Assembly <anyblok_wms_base.bloks.core.operation.assembly`
        whose name is given by the ``reverse_assembly`` key in the behaviour,
        with a default: ``'pack'``
        """
        gt = self.input.obj.type
        # TODO define a has_behaviour() API on goods_type
        ass_beh = gt.get_behaviour('assembly')
        if ass_beh is None:
            return False
        return self.reverse_assembly_name() in ass_beh

    def plan_revert_single(self, dt_execution, follows=()):
        """Plan reversal

        Currently, there is no way to specify extra inputs to be consumed
        by the reverse Assembly. As a consequence, Unpack reversal is only
        meaningful in the following cases:

        * wrapping material is not tracked in the system at all
        * wrapping material is tracked, and is not destroyed by the Unpack,
          so that it is both one of the Unpack outcomes, and one of the
          packing Assembly inputs.

        Also, currently the Assembly will have to take place exactly where the
        Unpack took place. This may not fit some concrete work organizations
        in warehouses.
        """
        # we need to pack the outcomes of reversals of downstream operations
        # together with our outcomes that aren't themselves inputs of a
        # downstream operation.
        pack_inputs = [out for op in follows for out in op.outcomes]
        # self.outcomes has actually only those outcomes that aren't inputs
        # of downstream operations
        # TODO maybe change that and create a new method instead
        # for API clarity

        pack_inputs.extend(self.leaf_outcomes())
        return self.registry.Wms.Operation.Assembly.create(
            outcome_type=self.input.obj.type,
            dt_execution=dt_execution,
            name=self.reverse_assembly_name(),
            inputs=pack_inputs)
