# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok import Declarations
from anyblok.relationship import Many2One

Mixin = Declarations.Mixin


@Declarations.register(Mixin)
class WmsInventoryOperation:
    """Add Wms.Inventory support on low-level Inventory Operations."""

    inventory = Many2One(model='Model.Wms.Inventory')
