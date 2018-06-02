"""Tests related to the devices module."""
# from configparser import ConfigParser
from unittest.mock import patch

import pytest
from device.device import (has_file_extension, process_hosts,
                           get_config_value, get_abs_file_path)
from device.command import ConfigParser, Logger, click


def test_process_hosts():
    """It returns a list of hosts."""
    assert process_hosts("192.168.1.1,192.168.44.11") == [
        '192.168.1.1',
        '192.168.44.11'
    ]


@pytest.mark.parametrize('path, expected', [
    ('/foo/bar/thing.txt', True),
    ('/foo/bar/other', False),
    ('/foo/bar/you.jpg', True),
    ('/foo/bar/yes.io', True),
    ('/foo/bar/main.c', True)
])
def test_has_file_extension(path, expected):
    """It tests whether the path contains a dot."""
    assert has_file_extension(path) == expected


@pytest.mark.parametrize('exception, message', [
    ('NoSectionError', 'No section for section_name: mock_name.'),
    ('NoOptionError', 'No option for section_name: mock_name.'),
])
@patch.object(ConfigParser, 'set')
@patch.object(Logger, 'debug')
@patch.object(click, 'prompt', return_value=1)
def test_set_config_option(prompt, logger, mock_set, exception, message):
    """It sets the expected config successfully."""
    config = ConfigParser()

    if exception == 'NoOptionError':
        config.add_section('section_name')

    get_config_value(config, 'section_name', 'mock_name', )

    logger.assert_called_once_with(message)
    prompt.assert_called_once_with(
        'Enter mock_name',
        default=None,
        type=click.STRING
    )
    mock_set.assert_called_once_with('section_name', 'mock_name', '1')


def test_get_abs_file_path():
    """It returns the expected file path."""
    assert get_abs_file_path(
        '/foo/bar',
        '/remote/path/file.txt'
    ) == '/foo/bar/file.txt'
