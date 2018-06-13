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


class WmsReservation(Blok):
    """Reservation facilities on top of the ``wms-core`` Blok.
    """
    version = version
    author = "Georges Racinet"

    required = ['wms-core']

    @classmethod
    def import_declaration_module(cls):
        from . import ns  # noqa
        from . import request  # noqa
        from . import reservation  # noqa
        from . import operation  # noqa

    @classmethod
    def reload_declaration_module(cls, reload):
        from . import ns
        reload(ns)
        from . import request
        reload(request)
        from . import reservation
        reload(reservation)
        from . import operation
        reload(operation)
