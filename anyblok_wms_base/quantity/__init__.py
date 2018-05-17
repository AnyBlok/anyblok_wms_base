# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok.blok import Blok


class WmsQuantity(Blok):
    """Enhance Goods with quantity field and related logic.

    Without this Blok, quantity information is derived by counting Goods
    records, which should be enough except when dealing with bulk goods or in
    cases where goods are rarely handled down to the unit, yet without using
    intermediate packaging.
    """
    version = '0.0.1'
    author = "Georges Racinet"
    required = ['wms-core']

    @classmethod
    def import_declaration_module(cls):
        from . import wms  # noqa
        from . import goods  # noqa
        from . import operation  # noqa

    @classmethod
    def reload_declaration_module(cls, reload):
        from . import wms
        reload(wms)
        from . import goods
        reload(goods)
        from . import operation
        reload(operation)
        operation.reload_declarations(reload)
