# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok import Declarations
from anyblok.column import String
from anyblok.column import Selection
from anyblok.column import Integer
from anyblok.column import Decimal
from anyblok.relationship import Many2One
from anyblok_postgres.column import Jsonb

from anyblok_wms_base.constants import GOODS_STATES

register = Declarations.register
Model = Declarations.Model


@register(Model.Wms.Goods)
class Properties:
    batch = String(label="Production batch reference")
