# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.

from anyblok import Declarations
from anyblok_wms_base.exceptions import OperationInputsError

register = Declarations.register
Operation = Declarations.Model.Wms.Operation


@register(Operation)
class Unpack:
    """Override to use quantity where needed."""

    def create_unpacked_goods(self, fields, spec):
        """Create just a record, bearing the total quantity.

        See also this method :meth:`in the base class
        <anyblok_wms_base.bloks.wms_core.operation.Unpack.create_unpacked_goods>`

        TODO: introduce a behaviour (available in spec) to create as many
        records as specified. Even if ``wms-quantity`` is installed, it might
        be more efficient for some Goods types. Use-case: some bulk handling
        alongside packed goods by the unit in the same facility.
        """
        Goods = self.registry.Wms.Goods
        target_qty = fields['quantity'] = spec['quantity'] * self.quantity
        existing_ids = spec.get('local_goods_ids')
        if existing_ids is not None:
            goods = [Goods.query().get(eid for eid in existing_ids)]
            if sum(g.quantity for g in goods) != target_qty:
                raise OperationInputsError(
                    self,
                    "final outcome specification {spec!r} has "
                    "'local_goods_ids' parameter, but they don't provide "
                    "the wished total quantity {target_qty} "
                    "Detailed input: {inputs[0]!r}",
                    spec=spec, target_qty=target_qty)
            return goods
        return [Goods.insert(**fields)]
