# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.

from anyblok import Declarations
from anyblok.column import Decimal
from anyblok.column import Integer
from anyblok.relationship import Many2One

register = Declarations.register
Operation = Declarations.Model.Wms.Operation


@register(Operation)
class Unpack(Operation):
    """Unpacking some Goods, creating new Goods records.

    What happens during unpacking is specified as behaviours of the
    Goods Type of the Goods being unpacked.

    For the time being, Unpacks will create the new Goods records in the
    same location. Downstream libraries and applications can prepend moves to
    unpacking areas, and/or append moves to final destinations.

    It's possible that we'd introduce an optional 'destination' column
    in the future, if the current schema is too inconvenient or bloats the
    database too much.
    """
    TYPE = 'wms_unpack'

    id = Integer(label="Identifier",
                 primary_key=True,
                 autoincrement=False,
                 foreign_key=Operation.use('id').options(ondelete='cascade'))
    goods = Many2One(model='Model.Wms.Goods', nullable=False)
    quantity = Decimal(label="Quantity")  # TODO non negativity constraint

    @classmethod
    def find_parent_operations(cls, goods=None, **kwargs):
        if goods is None:
            raise ValueError(
                "'goods' kwarg must be passed to Unpack.create()")
        return [goods.reason]

    @classmethod
    def check_create_conditions(cls, state, goods=None, quantity=None,
                                **kwargs):
        if goods is None:
            raise ValueError("'goods' kwarg must be passed to Unpack.create()")
        if quantity is None:
            raise ValueError("'quantity' kwarg must be passed "
                             "to Unpack.create()")
        if state == 'done' and goods.state != 'present':
            raise ValueError("Can't create an Unpack in state 'done' "
                             "for goods %r because of their state %r" % (
                                 goods, goods.state))
        assert 'unpack' in goods.type.behaviours

        # TODO specific exceptions
        if quantity > goods.quantity:
            raise ValueError(
                "Can't unpack a greater quantity (%r) "
                "than held in goods %r (which have quantity=%r)" % (
                    quantity, goods, goods.quantity))
        if quantity != goods.quantity:
            raise NotImplementedError(
                "Sorry not able to split Goods records yet")

    def after_insert(self):
        # TODO implement splitting
        Goods = self.registry.Wms.Goods
        GoodsType = Goods.Type
        packs = self.goods

        spec = packs.type.behaviours['unpack'].get('outcomes')
        if not spec:
            return
        type_ids = set(outcome['type'] for outcome in spec)
        packs_types = {gt.id: gt for gt in GoodsType.query().filter(
                       GoodsType.id.in_(type_ids)).all()}

        if self.state == 'done':
            packs.update(state='past', reason=self)
            for outcome_spec in spec:
                outcome = Goods.insert(
                    quantity=outcome_spec['quantity'] * self.quantity,
                    location=packs.location,
                    type=packs_types[outcome_spec['type']],
                    reason=self,
                    state='present')
                self.forward_props(outcome_spec, outcome),

        else:
            raise NotImplementedError

    def forward_props(self, spec, outcome):
        """Create a the properties for a given outcome (Goods line)

        :param spec: the relevant part of behaviour for this outcome
        :param outcome: just-created Goods instance
        :returns: None if no properties are to be created
        """
        packs = self.goods
        fwd_props = spec.get('forward_properties', ())
        req_props = spec.get('required_properties')

        if req_props and not packs.properties:
            # TODO precise exception
            raise ValueError(
                "Packs %s have no properties, yet its type %s "
                "requires these for Unpack operation: %r" % (
                    packs, packs.type, req_props))
        if not fwd_props:
            return
        for pname in fwd_props:
            pvalue = packs.get_property(pname)
            if pvalue is None:
                if pname not in req_props:
                    continue
            # TODO precise exception
                raise ValueError(
                    "Pack %s lacks the property %r "
                    "required by its type "
                    "for Unpack operation" % (packs, pname))
            outcome.set_property(pname, pvalue)
