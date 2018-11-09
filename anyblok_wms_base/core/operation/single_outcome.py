# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
"""Mixins for Operations that take exactly on PhysObj record as input.
"""

from anyblok import Declarations

Mixin = Declarations.Mixin
Model = Declarations.Model


@Declarations.register(Mixin)
class WmsSingleOutcomeOperation:
    """Mixin for Operations that produce a single outcome.

    This is synctactical sugar, allowing to work with such Operations as if
    Operations couldn't in general produce several outcomes.
    """

    @property
    def outcome(self):
        """Convenience attribute to return the unique outcome.
        """
        Avatar = self.registry.Wms.PhysObj.Avatar
        return Avatar.query().filter_by(outcome_of=self).one()
