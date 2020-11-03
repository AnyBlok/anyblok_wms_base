#!/usr/bin/env python3

import sys
import os
import platform
from sys import argv
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from subprocess import check_call

py_impl = platform.python_implementation()

VENV_BINDIR = os.path.dirname(sys.executable)


def valid_db_name(s):
    """Minimal validation for passed DB name."""
    if '"' in s:
        raise ValueError("%r is not suitable for a database name" % s)
    return s


def dropdb(db):
    """Drop database with no error if it exists."""
    print("Dropping tests database %r if already existing" % db)
    check_call(('psql', '-c',
                'DROP DATABASE IF EXISTS "%s"' % db,
                'postgres'))


def createdb(*bloks):
    db = os.environ['ANYBLOK_DATABASE_NAME']
    print("Creating tests database %r, "
          "installing bloks: %r" % (db, bloks))
    check_call(('psql', '-c',
                'CREATE DATABASE "%s"' % db,
                'postgres'))
    check_call((
        'anyblok_updatedb', '--install-bloks') + tuple(bloks))
    print()


def install_bloks(*bloks):
    print("Installing bloks: " + ', '.join(bloks))
    check_call((os.path.join(VENV_BINDIR, 'anyblok_updatedb'),
                '--install-bloks') + tuple(bloks))
    print()


def nosetests(paths, options, cover_erase=False):
    print("Launching tests from paths: " + ' '.join(paths))
    cmd = [os.path.join(VENV_BINDIR, 'nosetests'),
           '--with-anyblok-bloks',
           '--with-coverage',
           '--cover-tests',
           '--cover-package', 'anyblok_wms_base',
           '--cover-html', '--cover-html-dir', '/tmp/COVER-wms']
    if cover_erase:
        cmd.append('--cover-erase')
    cmd.extend(paths)
    cmd.extend(options)
    check_call(cmd)


def doctests(paths, options, cover_erase=False):
    print("Lauching doctests from paths: " + ' '.join(paths))
    cmd = [os.path.join(VENV_BINDIR, 'nosetests'),
           '--with-doctest',
           '--with-coverage', '--cover-html', '--cover-package',
           'anyblok_wms_base', '--cover-html-dir', '/tmp/COVER-wms']
    if cover_erase:
        cmd.append('--cover-erase')
    cmd.extend(paths)
    cmd.extend(options)
    check_call(cmd)


def run(db_name, nose_additional_opts):
    if py_impl == 'PyPy':
        driver = 'postgresql+psycopg2cffi'
    else:
        driver = 'postgresql'
    os.environ.update(ANYBLOK_DATABASE_NAME=db_name,
                      ANYBLOK_DATABASE_DRIVER=driver)

    awb_dir = os.path.join(os.path.dirname(sys.argv[0]), 'anyblok_wms_base')
    doctests([os.path.join(awb_dir, 'utils.py'),
              os.path.join(awb_dir, 'dbapi.py'),
              ],
             nose_additional_opts, cover_erase=True)
    bloks_dir = awb_dir
    dropdb(db_name)
    createdb('wms-core', 'test-wms-goods-batch-ref')
    nosetests((os.path.join(awb_dir, 'utils.py'),
               os.path.join(bloks_dir, 'core')),
              nose_additional_opts)
    install_bloks('wms-inventory')
    nosetests((os.path.join(bloks_dir, 'inventory'), ),
              nose_additional_opts)
    install_bloks('wms-reservation')
    nosetests((os.path.join(bloks_dir, 'reservation'), ),
              nose_additional_opts)
    # some Inventory.Action tests are run only if wms-reservation is installed
    # and it's a good idea to check the others with wms-reservation, too.
    nosetests((os.path.join(bloks_dir, 'inventory',
                            'tests', 'test_action.py'), ),
              nose_additional_opts)

    dropdb(db_name)
    createdb('wms-quantity')
    nosetests((os.path.join(bloks_dir, 'quantity'),
               ),
              nose_additional_opts)


parser = ArgumentParser(description="Run tests for all bloks with coverage",
                        epilog="To pass additional arguments to nosetests "
                        "separate them with '--'",
                        formatter_class=ArgumentDefaultsHelpFormatter)
parser.add_argument('--db-name', '--dbname', default="test_anyblok_wms_all",
                    type=valid_db_name)
parser.add_argument('--cover-html', action='store_true',
                    help="If set, buidld an HTML version of coverage report")
parser.add_argument('--cover-html-dir', default="/tmp/COVER-wms",
                    help="Directory to build HTML coverage report in")


try:
    double_dash = argv.index('--')
except ValueError:
    args, nose_additional_opts = argv[1:], ()
else:
    args, nose_additional_opts = argv[1:double_dash], argv[double_dash + 1:]

arguments = parser.parse_args(args)
if arguments.cover_html:
    nose_additional_opts.extend((
        '--cover-html', '--cover-html-dir', arguments.cover_html_dir))

run(arguments.db_name, nose_additional_opts)

if arguments.cover_html:
    print(
        "To see HTML cover report, point your browser at "
        "file://" + os.path.realpath(arguments.cover_html_dir) +
        '/index.html')
