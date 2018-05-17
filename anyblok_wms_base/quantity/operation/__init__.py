# -*- coding: utf-8 -*-
# flake8: noqa
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.

from . import split
from . import aggregate
from . import splitter
from . import arrival
from . import move
from . import unpack


def reload_declarations(reload):
    reload(split)
    reload(aggregate)
    reload(splitter)
    reload(arrival)
    reload(move)
    reload(unpack)
