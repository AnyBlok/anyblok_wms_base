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

from anyblok_wms_base.exceptions import OperationInputsError

register = Declarations.register
Mixin = Declarations.Mixin
Operation = Declarations.Model.Wms.Operation


@register(Operation)
class Unpack(Mixin.WmsSingleInputOperation, Operation):
    """Unpacking some goods, creating new Goods and Avatar records.

    This is a destructive Operation, in the usual mild sense: once it's done,
    the input Goods Avatars is in the ``past`` state, and their underlying Goods
    have no new Avatars. It is
    meant to be reversible through appropriate Pack / Assembly Operations,
    which are not implemented yet at the time being.

    What happens during unpacking is specified as behaviours of the
    Goods Type of the Goods being unpacked.

    For the time being, Unpacks will create the new Avatar records
    in the same location. Downstream libraries and applications can prepend
    moves to unpacking areas, and/or append moves to final destinations.

    It's possible that we'd introduce an optional 'destination' column
    in the future, if the current schema is too inconvenient or bloats the
    database too much.
    """
    TYPE = 'wms_unpack'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))

    @classmethod
    def check_create_conditions(cls, state, dt_execution,
                                inputs=None, quantity=None, **kwargs):
        super(Unpack, cls).check_create_conditions(
            state, dt_execution, inputs=inputs,
            quantity=quantity,
            **kwargs)

        goods_type = inputs[0].type
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
        packs.update(state='past', reason=self)

    def after_insert(self):
        Goods = self.registry.Wms.Goods
        GoodsType = Goods.Type
        packs = self.input
        dt_execution = self.dt_execution
        spec = self.get_outcome_specs()
        type_ids = set(outcome['type'] for outcome in spec)
        outcome_types = {gt.id: gt for gt in GoodsType.query().filter(
            GoodsType.id.in_(type_ids)).all()}

        outcome_state = 'present' if self.state == 'done' else 'future'
        if self.state == 'done':
            packs.update(state='past', reason=self)
        for outcome_spec in spec:
            # TODO what would be *really* neat would be to be able
            # to recognize the goods after a chain of pack/unpack
            goods_fields = dict(
                quantity=outcome_spec['quantity'] * self.quantity,
                type=outcome_types[outcome_spec['type']])
            clone = outcome_spec.get('forward_properties') == 'clone'
            if clone:
                goods_fields['properties'] = packs.goods.properties
            outcome = Goods.insert(**goods_fields)
            Goods.Avatar.insert(goods=outcome,
                                location=packs.location,
                                reason=self,
                                dt_from=dt_execution,
                                dt_until=packs.dt_until,
                                state=outcome_state)
            if not clone:
                self.forward_props(outcome_spec, outcome)
        packs.dt_until = dt_execution

    def forward_props(self, spec, outcome):
        """Handle the properties for a given outcome (Goods record)

        :param spec: the relevant part of behaviour for this outcome
        :param outcome: just-created Goods instance
        """
        packs = self.input.goods
        fwd_props = spec.get('forward_properties', ())
        req_props = spec.get('required_properties')

        if req_props and not packs.properties:
            raise OperationInputsError(
                self,
                "Packs {inputs[0]} have no properties, yet their type {type} "
                "requires these for Unpack operation: {req_props}",
                type=packs.type, req_props=req_props)
        if not fwd_props:
            return
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
            outcome.set_property(pname, pvalue)

    def get_outcome_specs(self):
        """Produce a complete behaviour for outcomes and their properties.

        Unless ``uniform_outcomes`` is set to ``True``,
        the outcomes of the Unpack are obtained by merging those defined in
        the Goods Types behaviour and in the packs (``self.input``) properties.

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
        aren't even read, they but simply
        cloned (referenced again) in the outcomes. This should be better
        for performance in high volume operation.
        The same can be achieved on a given outcome by specifying the
        special ``'clone'`` value for ``forward_properties``.

        Otherwise, the ``forward_properties`` and ``required_properties``
        unpack behaviour from the Goods Type of the packs (``self.input``)
        are merged with those of the outcomes, so that, for instance
        ``forward_properties`` have three key/value sources:

        - top-level at the Goods Type ``unpack`` behaviour
        - in each outcome of the Goods Type
        - in each outcome of the Goods record (``unpack_outcomes`` property)

        Here's a use-case: imagine the some purchase order reference is
        tracked as property ``po_ref`` (could be important for accounting).

        A Goods Type representing an incoming package holding various Goods
        could specify that ``po_ref`` must be forwarded upon Unpack in all
        cases. For instance, a Goods record with that type could then
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
        behaviour = packs.type.behaviours['unpack']
        specs = behaviour.get('outcomes', [])[:]
        if behaviour.get('uniform_outcomes', False):
            for outcome in specs:
                outcome['forward_properties'] = 'clone'
            return specs

        specific_outcomes = packs.get_property('unpack_outcomes', ())
        specs.extend(specific_outcomes)
        if not specs:
            raise OperationInputsError(
                self,
                "unpacking {inputs[0]} yields no outcomes. "
                "Type {type} 'unpack' behaviour: {behaviour}, "
                "specific outcomes from Goods properties: "
                "{specific}",
                type=packs.type, behaviour=behaviour,
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
        """Remove the newly created Goods, not only their Avatars."""
        self.reset_inputs_original_values()
        self.registry.flush()
        all_goods = set()
        # TODO PERF in two queries using RETURNING, or be braver and
        # make the avatars cascade
        for avatar in self.outcomes:
            all_goods.add(avatar.goods)
            avatar.delete()
        for goods in all_goods:
            goods.delete()
