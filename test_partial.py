#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This file is a part of the AnyBlok / WMS Base project
#
#    Copyright (C) 2018 Georges Racinet <gracinet@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
import os
import sys
import platform
import argparse
import subprocess

py_impl = platform.python_implementation()
if py_impl == 'PyPy':
    DEFAULT_DRIVER = 'postgresql+psycopg2cffi'
else:
    DEFAULT_DRIVER = 'postgresql'

os.chdir(os.path.dirname(__file__))
for path in ('.noseids', '.coverage'):
    if os.path.exists(path):
        os.unlink(path)

BASEPKG = 'anyblok_wms_base'
BLOKS = {'wms-core': 'core',
         'wms-reservation': 'reservation',
         'wms-quantity': 'quantity'
         }

parser = argparse.ArgumentParser(
   description="Run tests with coverage "
   "for a subpackage of {base} only".format(base=BASEPKG),
   epilog="Examples: "
          "./test_partial wms-core "
          "./test_partial wms-core --subpkg physobj "
)
parser.add_argument('blok', choices=BLOKS.keys())
parser.add_argument('--subpkg',
                    help="Subpackage of the given Blok to run for. "
                    "Example: 'models.preparation'. ")
parser.add_argument('--db-driver-name', default=DEFAULT_DRIVER,
                    help="SQLAlchemy PostgreSQL driver, see "
                    "https://docs.sqlalchemy.org/en/latest"
                    "/dialects/postgresql.html")
parser.add_argument('-f', '--fresh-db', action='store_true',
                    help="Drop the database if it exists before run")


arguments = parser.parse_args()

blok = arguments.blok
blok_pkg = '.'.join((BASEPKG, BLOKS[blok]))

sub = arguments.subpkg

cover_pkg = '.'.join((blok_pkg, sub)) if sub else blok_pkg
test_pkg = cover_pkg

venv_dir = os.path.dirname(sys.executable)

cover_html_dir = "/tmp/COVER-" + cover_pkg
db_name = 'test_awb_' + cover_pkg

if arguments.fresh_db:
    subprocess.check_call(('psql', '-c',
                           'DROP DATABASE IF EXISTS "%s"' % db_name,
                          'postgres'))

databases = [d.strip()
             for d in subprocess.check_output(
                     ('psql', '-t',
                      '-c', 'SELECT datname FROM pg_catalog.pg_database',
                      'postgres')).decode().splitlines()]

if db_name not in databases:
    cmd = 'anyblok_createdb'
else:
    cmd = 'anyblok_updatedb'
subprocess.check_call((cmd,
                       '--db-driver-name', arguments.db_driver_name,
                       '--db-name', db_name,
                       '--install-or-update-bloks',
                       'test-wms-goods-batch-ref',
                       blok))

plugin_cmd = [os.path.join(venv_dir, 'nosetests'),
              '--with-anyblok-bloks',
              '--anyblok-db-driver-name', arguments.db_driver_name,
              "--anyblok-db-name", db_name,
              test_pkg,
              "--with-id",
              "-vs",
              "--with-coverage", "--cover-erase",
              "--cover-package", cover_pkg,
              "--cover-html",
              "--cover-html-dir", cover_html_dir
              ]

result = subprocess.call(plugin_cmd)
print("\nFor HTML coverage report, open file://%s/index.html" % cover_html_dir)
anyblok_nose = "anyblok_nose --db-driver-name %s --db-name %s -- %s" % (
    arguments.db_driver_name, db_name, test_pkg)
if result == 0:  # sucess
    print("\nTo run again with different options, maybe incompatible with the "
          "Nose plugin, or a precise test, do something based on: ")
    print("    " + anyblok_nose)
else:
    print("\nTo rerun incrementally, do: ")
    print("    " + anyblok_nose + ' --failed')
sys.exit(result)
