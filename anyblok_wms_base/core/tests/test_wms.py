# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.

from anyblok_wms_base.testing import BlokTestCase


class TestWms(BlokTestCase):
    """Test Model.Wms methods not related to quantities.

    For quantities of physical objects, see :mod:`test_quantity`.
    """

    def setUp(self):
        self.Wms = self.registry.Wms

    def test_create_root_container_wrong_type(self):
        gt = self.Wms.PhysObj.Type.insert(code='NOT-A-CONTAINER')
        with self.assertRaises(ValueError):
            self.Wms.create_root_container(gt)
