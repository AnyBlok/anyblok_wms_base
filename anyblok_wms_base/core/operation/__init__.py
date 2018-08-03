# -*- coding: utf-8 -*-
# flake8: noqa
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.

def import_declarations(reload=None):
    from . import ns
    from . import base
    from . import single_input
    from . import arrival
    from . import departure
    from . import move
    from . import unpack
    from . import assembly
    from . import apparition
    from . import disparition
    from . import teleportation

    if reload is not None:
        reload(ns)
        reload(single_input)
        reload(arrival)
        reload(departure)
        reload(move)
        reload(unpack)
        reload(assembly)
        reload(apparition)
        reload(disparition)
        reload(teleportation)
