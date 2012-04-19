"""
clihelper-tests.py

"""
__author__ = 'Gavin M. Roy'
__email__ = 'gmr@myyearbook.com'
__since__ = '2012-04-18'

import copy
import daemon
import grp
import mock
import logging_config
import optparse
import os
import signal
import sys
import time
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import yaml

sys.path.insert(0, '..')
import clihelper

_WAKE_INTERVAL = 5
_CONFIG = {clihelper._APPLICATION: {'wake_interval': _WAKE_INTERVAL},
           clihelper._DAEMON: {'user': 'root',
                               'group': 'wheel',
                               'pidfile': '/foo/bar/'},
           clihelper._LOGGING: {'Formatters': [], 'Filters': [],
                                'Handlers': [], 'Loggers': []}}


class CLIHelperTests(unittest.TestCase):

    def _setup_mock_load_config(self):
        self._mock_load_config = mock.Mock(return_value=_CONFIG)
        self._load_config_patcher = mock.patch('clihelper._load_config',
                                               self._mock_load_config)
        self._load_config_patcher.start()
        self.addCleanup(self._load_config_patcher.stop)

    def _setup_mock_logging_config(self):
        self._mock_logging_config = mock.Mock(spec=logging_config.Logging)
        self._logging_config_patcher = mock.patch('logging_config.Logging',
                                                  self._mock_logging_config)
        self._logging_config_patcher.start()
        self.addCleanup(self._logging_config_patcher.stop)

    def _return_context(self):
        return self._daemon_context

    def _return_optparse(self):
        return self._optparse

    def _setup_mock_daemon_context(self):
        self._daemon_context = mock.Mock(spec=daemon.DaemonContext)
        self._daemon_context_patcher = \
            mock.patch('clihelper._new_daemon_context', self._return_context)
        self._daemon_context_patcher.start()
        self.addCleanup(self._daemon_context_patcher.stop)

    def _setup_mock_new_option_parser(self):
        self._optparse = mock.Mock(spec=optparse.OptionParser)
        self._optparse.parse_args = mock.Mock(return_value = (self._options,
                                                              list()))
        self._optparse_patcher = mock.patch('clihelper._new_option_parser',
                                            self._return_optparse)
        self._optparse_patcher.start()
        self.addCleanup(self._optparse_patcher.stop)

    def _mock_options(self):
        mock_options = mock.Mock(spec=optparse.Values)
        mock_options.foreground = False
        mock_options.configuration = 'TEST'
        return mock_options

    def setUp(self):
        clihelper._CONFIG_FILE = '/dev/null'
        self._options = self._mock_options()
        self._setup_mock_daemon_context()
        self._setup_mock_load_config()
        self._setup_mock_logging_config()
        self._setup_mock_new_option_parser()
        self._controller = clihelper.Controller(self._options, list())
        clihelper.set_controller(self._controller)

    def tearDown(self):
        clihelper._CONFIG_FILE = None
        del self._controller

    def test_get_configuration(self):
        self.assertEqual(clihelper._get_configuration(), _CONFIG)

    def test_get_configuration_invalid_config(self):
        _BAD_CONFIG = copy.deepcopy(_CONFIG)
        del _BAD_CONFIG[clihelper._LOGGING]
        self._mock_load_config.return_value = _BAD_CONFIG
        self.assertRaises(ValueError, clihelper._get_configuration)
        self._mock_load_config.return_value = _CONFIG

    def test_get_daemon_config(self):
        self.assertEqual(clihelper._get_daemon_config(),
                         _CONFIG[clihelper._DAEMON])

    def test_get_logging_config(self):
        self.assertEqual(clihelper._get_logging_config(),
                         _CONFIG[clihelper._LOGGING])

    def test_get_pidfile_path(self):
        print _CONFIG
        self.assertEqual(clihelper._get_pidfile_path(),
                         _CONFIG[clihelper._DAEMON]['pidfile'])

    def test_get_default_pidfile(self):
        _BAD_CONFIG = copy.deepcopy(_CONFIG)
        del _BAD_CONFIG[clihelper._DAEMON]['pidfile']
        self._mock_load_config.return_value = _BAD_CONFIG
        self.assertEqual(clihelper._get_pidfile_path(),
                         clihelper._PIDFILE % clihelper._APPNAME)
        self._mock_load_config.return_value = _CONFIG

    def test_get_gid(self):
        value = 'wheel'
        self.assertEqual(clihelper._get_gid(value), grp.getgrnam(value).gr_gid)

    def test_get_daemon_context(self):
        context = clihelper._get_daemon_context()
        self.assertIsInstance(context, daemon.DaemonContext)

    def test_cli_options(self):
        clihelper.setup('Foo', 'Bar', '1.0')
        options, arguments = clihelper._cli_options(None)
        self.assertIsInstance(options, optparse.Values)

    def test_cli_options_with_callback(self):
        callback = mock.Mock()
        clihelper.setup('Foo', 'Bar', '1.0')
        clihelper._cli_options(callback)
        self.assertTrue(callback.called)

    def test_parse_yaml(self):
        content = yaml.dump(_CONFIG)
        result = clihelper._parse_yaml(content)
        self.assertEqual(result, _CONFIG)

    def test_read_config_file(self):
        filename = '/tmp/clihelper.test.%.2f' % time.time()
        content = yaml.dump(_CONFIG)
        with open(filename, 'w') as handle:
            handle.write(content)
        clihelper.set_configuration_file(filename)
        result = clihelper._read_config_file()
        os.unlink(filename)
        self.assertEqual(result, content)


    def test_get_uid(self):
        self.assertEqual(clihelper._get_uid('root'), 0)

    def test_set_appname(self):
        clihelper.set_appname(__name__)
        self.assertEqual(clihelper._APPNAME, __name__)

    def test_set_configuration_file(self):
        filename = '/dev/null'
        clihelper.set_configuration_file(filename)
        self.assertEqual(clihelper._CONFIG_FILE, filename)

    def test_set_empty_configuration_file(self):
        self.assertRaises(ValueError, clihelper.set_configuration_file, None)

    def test_set_controller(self):
        self.assertEqual(clihelper._CONTROLLER, self._controller)

    def test_set_description(self):
        clihelper.set_description(self.__class__.__name__)
        self.assertEqual(clihelper._DESCRIPTION, self.__class__.__name__)

    def test_set_version(self):
        clihelper.set_version(__since__)
        self.assertEqual(clihelper._VERSION, __since__)

    def test_setup_appname(self):
        value = 'TestAppName:%.2f' % time.time()
        clihelper.setup(value, None, None)
        self.assertEqual(clihelper._APPNAME, value)

    def test_setup_description(self):
        value = 'TestDescription:%.2f' % time.time()
        clihelper.setup(None, value, None)
        self.assertEqual(clihelper._DESCRIPTION, value)

    def test_setup_version(self):
        value = 'TestVersion:%.2f' % time.time()
        clihelper.setup(None, None, value)
        self.assertEqual(clihelper._VERSION, value)

    def test_validate_config_file(self):
        clihelper._CONFIG_FILE = '/tmp/clihelper-test-%.2f' % time.time()
        with open(clihelper._CONFIG_FILE, 'w') as handle:
            handle.write('Foo\n')
        response = clihelper._validate_config_file()
        os.unlink(clihelper._CONFIG_FILE)
        clihelper._CONFIG_FILE = '/dev/null'
        self.assertTrue(response)

    def test_validate_config_file_not_empty(self):
        clihelper._CONFIG_FILE = None
        self.assertRaises(ValueError, clihelper._validate_config_file)
        clihelper._CONFIG_FILE = '/dev/null'

    def test_validate_config_file_does_not_exist(self):
        clihelper._CONFIG_FILE = '/tmp/clihelper-test-%.2f' % time.time()
        self.assertRaises(OSError, clihelper._validate_config_file)
        clihelper._CONFIG_FILE = '/dev/null'

    def test_setup_logging(self):
        clihelper._setup_logging(False)
        self.assertTrue(self._mock_logging_config.called)

    def test_on_sighup(self):
        frame = time.time()
        with mock.patch.object(self._controller, '_on_sighup') as sighup:
            clihelper._on_sighup(signal.SIGHUP, frame)
            sighup.assert_called_with(frame)

    def test_on_sigterm(self):
        frame = time.time()
        with mock.patch.object(self._controller, '_on_sigterm') as sigterm:
            clihelper._on_sigterm(signal.SIGTERM, frame)
            sigterm.assert_called_with(frame)

    def test_on_sigusr1(self):
        frame = time.time()
        with mock.patch.object(self._controller, '_on_sigusr1') as sigusr1:
            clihelper._on_sigusr1(signal.SIGUSR1, frame)
            sigusr1.assert_called_with(frame)

    def test_on_sigusr2(self):
        frame = time.time()
        with mock.patch.object(self._controller, '_on_sigusr2') as sigusr2:
            clihelper._on_sigusr2(signal.SIGUSR2, frame)
            sigusr2.assert_called_with(frame)

    def test_controller_new_instance_has_idle_state(self):
        self.assertEqual(self._controller._state,
                         clihelper.Controller._STATE_IDLE)

    def test_controller_new_instance_is_not_running(self):
        self.assertFalse(self._controller.is_running)

    def test_controller_new_instance_is_not_shutting_down(self):
        self.assertFalse(self._controller.is_shutting_down)

    def test_controller_set_state_invalid_option(self):
        self.assertRaises(ValueError, self._controller._set_state, -1)


    def test_controller_get_application_config(self):
        self.assertEqual(self._controller._get_application_config(),
                         _CONFIG[clihelper._APPLICATION])

    def test_controller_get_config_return_value(self):
        key = 'wake_interval'
        self.assertEqual(self._controller._get_config(key),
                          _CONFIG[clihelper._APPLICATION][key])

    def test_controller_get_config_calls_get_configuration(self):
        with mock.patch('clihelper._get_configuration') as mock_function:
            mock_function.return_value = _CONFIG
            self._controller._get_config('wake_interval')
            self.assertTrue(mock_function.called)

    def test_controller_get_wake_interval(self):
        self.assertEqual(self._controller._get_wake_interval(),
                          _CONFIG[clihelper._APPLICATION]['wake_interval'])


class NonePatchedTests(unittest.TestCase):

    def test_new_context(self):
        self.assertIsInstance(clihelper._new_daemon_context(),
                              daemon.DaemonContext)

    def test_new_option_parser(self):
        self.assertIsInstance(clihelper._new_option_parser(),
                              optparse.OptionParser)

    def test_load_config_file(self):
        filename = '/tmp/clihelper.test.%.2f' % time.time()
        content = yaml.dump(_CONFIG)
        with open(filename, 'w') as handle:
            handle.write(content)
        clihelper.set_configuration_file(filename)
        result = clihelper._load_config()
        os.unlink(filename)
        self.assertEqual(result, _CONFIG)