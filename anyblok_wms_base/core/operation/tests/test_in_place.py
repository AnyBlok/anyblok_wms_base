# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from anyblok_wms_base.testing import WmsTestCaseWithPhysObj
from anyblok_wms_base.exceptions import (
    OperationInputsError,
    )


class TestInPlaceOperation(WmsTestCaseWithPhysObj):
    """High level tests for alteration of chains of planned Operations."""

    def setUp(self):
        super().setUp()
        self.Move = self.Operation.Move

    def test_inconsistent_input_location_changed(self):
        """Test input_location_changed() where inputs locations now differ.

        This test is artificial, because we don't currently have in
        wms-core an Operation with several inputs that derives from the
        in place mixin.
        (Assembly is designed not to, so that Assemblies from different
        locations are possible in applicative code)
        """
        in_place = self.Operation.Observation.create(input=self.avatar)
        other_av = self.Operation.Arrival.create(
            location=self.stock,
            physobj_type=self.avatar.obj.type).outcome
        in_place.link_inputs((other_av, ))
        with self.assertRaises(OperationInputsError) as arc:
            in_place.input_location_altered()
        exc = arc.exception
        self.assertEqual(set(exc.kwargs['inputs']), {self.avatar, other_av})
        self.assertEqual(set(exc.kwargs['locations']),
                         {self.incoming_loc, self.stock})


del WmsTestCaseWithPhysObj
