# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
import logging

from anyblok.blok import Blok
from .. import version
from . import physobj
from . import operation

logger = logging.getLogger(__name__)


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

    def pre_migration(self, latest_version):  # pragma: no cover
        if latest_version is None:
            return
        if latest_version < '0.8.0.dev1':
            self.migr_physobj()

    def migr_physobj(self):  # pragma: no cover
        logger.info("Premigration: renaming of Goods to PhysObj")
        execute = self.registry.execute
        # as of this writing, AnyBlok's pre_migration is not before
        # the creation of new tables TODO make an issue of that
        # TODO the new tables are empty, of course, yet adding a safety
        # check would be better.
        # the CASCADE will drop wms_physobj, then properties and avatars
        physobj_suffixes = ('', '_type', '_avatar', '_properties')
        for suffix in physobj_suffixes:
            execute("DROP TABLE IF EXISTS wms_physobj{0} CASCADE".format(
                suffix))
        execute("ALTER TABLE wms_goods RENAME TO wms_physobj")
        execute("ALTER TABLE wms_goods_type RENAME TO wms_physobj_type")
        execute("ALTER TABLE wms_goods_avatar RENAME TO wms_physobj_avatar")
        execute("ALTER TABLE wms_goods_properties "
                "RENAME TO wms_physobj_properties")
        execute("ALTER TABLE wms_physobj_avatar "
                "RENAME COLUMN goods_id TO obj_id")

        # Updating primary key names
        #   (not an absolute necessity, but can maybe avoid problems in the
        #   future)
        #   here it would be neat to import MigrationConstraintPrimaryKey
        #   from anyblok.migration, so that we don't need to guess the name of
        #   the primary key index, but it expects a Table object. We could of
        #   course fake it, but that's a bit convoluted for the benefits
        for suffix in physobj_suffixes:
            execute("ALTER INDEX anyblok_pk_wms_goods{0} "
                    " RENAME TO anyblok_pk_wms_physobj{0}".format(suffix))

        # Foreign key constraints are now ill-named, next migration will
        # delete and recreate them, that's not an issue with current volumes
        # but it would be at a later stage of development
        # TODO provide AnyBlok facilities for migrations that are just renames

    @classmethod
    def import_declaration_module(cls):
        import_declarations()

    @classmethod
    def reload_declaration_module(cls, reload):
        import_declarations(reload=reload)
