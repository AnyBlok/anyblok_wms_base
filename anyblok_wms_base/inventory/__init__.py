# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok.blok import Blok
from anyblok_wms_base import version


def import_declarations(reload=None):
    from . import order
    from . import operation
    from . import node
    if reload is not None:
        reload(order)
        reload(operation)
        reload(node)


class WmsInventory(Blok):
    """Inventory management facilities
    """
    version = version
    author = "Georges Racinet"

    required = ['wms-core']

    @classmethod
    def import_declaration_module(cls):
        import_declarations()

    @classmethod
    def reload_declaration_module(cls, reload):
        import_declarations(reload=reload)
