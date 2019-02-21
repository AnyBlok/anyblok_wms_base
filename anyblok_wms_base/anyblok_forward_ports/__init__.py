# -*- coding: utf-8 -*-
# pragma: no cover
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from unittest import SkipTest


def skip_unless_bloks_installed(*bloks):
    def bloks_decorator(testmethod):
        def wrapped(self):
            Blok = self.registry.System.Blok
            for blok_name in bloks:
                blok = Blok.query().get(blok_name)
                if blok.state != 'installed':
                    raise SkipTest("Blok %r is not installed" % blok_name)
            return testmethod(self)
        # necessary not to be ignored by test runner
        wrapped.__name__ = testmethod.__name__
        return wrapped
    return bloks_decorator
