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
from anyblok.column import Integer
from anyblok.relationship import Many2One

register = Declarations.register
Model = Declarations.Model


@register(Model.Wms)
class Items:
    type = Many2One(model='Model.Wms.Items.Type')
    code = String(label="Identifying code", primary_key=True)


@register(Model.Wms.Items)
class Type:
    """Type of WMS items"""
    id = Integer(label="Identifier", primary_key=True)
    label = String(label=u"Label")
