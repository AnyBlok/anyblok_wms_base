# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok.blok import Blok
from .. import version
from . import physobj
from . import operation


def import_declarations(reload=None):
    from . import wms
    if reload is not None:
        reload(wms)
    operation.import_declarations(reload=reload)
    physobj.import_declarations(reload=reload)


class WmsCore(Blok):
    """Core concepts for WMS and logistics.
    """
    version = version
    author = "Georges Racinet"

    @classmethod
    def import_declaration_module(cls):
        import_declarations()

    @classmethod
    def reload_declaration_module(cls, reload):
        import_declarations(reload=reload)
