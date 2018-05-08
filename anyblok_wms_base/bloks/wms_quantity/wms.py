# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from sqlalchemy import func
from anyblok import Declarations


@Declarations.register(Declarations.Model)
class Wms:
    """Override to replace quantity counting by summation"""

    @classmethod
    def base_quantity_query(cls):
        """Return a base query fit for summing Goods.Quantity."""
        Goods = cls.registry.Wms.Goods
        Avatar = Goods.Avatar
        # TODO distinguish quantity on Avatars from those on Goods?
        return Avatar.query(func.sum(Goods.quantity)).join(Avatar.goods)
