# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
"""This module contains unreleased AnyBlok test helpers.

This will allow us to use and refine them before they are properly
released within AnyBlok.
"""
from sqlalchemy import event
from anyblok.tests.testcase import BlokTestCase


class SharedDataTestCase(BlokTestCase):

    @classmethod
    def setUpClass(cls):
        super(SharedDataTestCase, cls).setUpClass()
        cls.pre_data_savepoint = cls.registry.begin_nested()
        try:
            cls.setUpSharedData()
        except Exception as exc:  # pragma: no cover
            # this code path is tested in the unreleased AnyBlok version
            # but of course no anyblok_wms_base test has such errors
            cls.tearDownClass()
            raise

    @classmethod
    def setUpSharedData(cls):
        """To be implemented by concrete test classes."""

    @classmethod
    def make_testcase_savepoint(cls, session=None):
        if session is None:
            session = cls.registry
        cls.testcase_savepoint = session.begin_nested()

    def setUp(self):
        # we don't want to execute BlokTestCase.setUp(), only its parent's:
        super(BlokTestCase, self).setUp()
        # tearDown is not called in case of errors in setUp, but these are:
        self.addCleanup(self.callCleanUp)
        self.make_testcase_savepoint()

        @event.listens_for(self.registry.session, "after_transaction_end")
        def restart_savepoint(session, transaction):
            session.expire_all()
            if transaction is self.testcase_savepoint:
                self.make_testcase_savepoint()
        self.savepoint_restarter = restart_savepoint

    @classmethod
    def tearDownClass(cls):
        cls.pre_data_savepoint.rollback()
        super(SharedDataTestCase, cls).tearDownClass()

    def tearDown(self):
        """Roll back the session """
        super(BlokTestCase, self).tearDown()
        self.testcase_savepoint.rollback()
        self.registry.System.Cache.invalidate_all()
        event.remove(self.registry.session, "after_transaction_end",
                     self.savepoint_restarter)
        self._transaction_case_teared_down = True
