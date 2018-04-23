# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.

from anyblok import Declarations

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
        records as the. Even if ``wms-quantity`` is installed, it might be
        more efficient for some Goods types. Use-case: some bulk handling
        alongside packed goods by the unit in the same facility.
        """
        Goods = self.registry.Wms.Goods
        fields['quantity'] = spec['quantity'] * self.quantity
        return [Goods.insert(**fields)]
