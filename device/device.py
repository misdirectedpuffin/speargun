import os
import sys
from configparser import NoOptionError, NoSectionError

import click
from gevent import joinall
from logbook import Logger, StreamHandler
from pssh.clients import ParallelSSHClient, SSHClient
from pssh.utils import load_private_key

StreamHandler(sys.stdout).push_application()
logger = Logger(__name__)


def get_config_value(config, section_name, name, prompt_type=click.STRING):
    """Return the new value to be set in config

    `hosts` requires multiple values, so we prompt for new ones in case
    a comma delimited string of hosts was not specified.
    """
    current = None
    try:
        current = config.get(section_name, name)
    except NoSectionError:
        logger.debug(f'No section for {section_name}: {name}.')
        config.add_section(section_name)
    except NoOptionError:
        logger.debug(f'No option for {section_name}: {name}.')

    finally:
        if name in ('hosts', 'remote'):
            unfinished = True
            new = []
            while unfinished:
                new.append(
                    click.prompt(
                        f'Enter {name}',
                        default=current,
                        type=prompt_type
                    )
                )
                message = f'Would you like to add another {name}?'
                unfinished = click.confirm(message)
            return ','.join(new)
        return click.prompt(
            f'Enter {name}',
            default=current,
            type=prompt_type
        )


def process_hosts(hosts: str):
    """Return a list of hosts from config"""
    return hosts.split(',')


def has_file_extension(path):
    """Return True if the path ending contains a dot."""
    end = path.split('/')[-1].lower()
    return '.' in end


def get_pssh_client(host, private_key_path, single_copy=False, port=8022, user='root'):
    if single_copy and isinstance(host, str):
        logger.debug('Trying single copy')
        return SSHClient(
            host,
            port=port,
            pkey=load_private_key(private_key_path),
            user=user
        )

    return ParallelSSHClient(
        host,
        port=port,
        pkey=load_private_key(private_key_path),
        user=user
    )


def make_greenlets(client, local, remotes, single_copy=False):
    for remote in remotes.split(','):
        logger.debug(f'Remotes: {remote}')
        greenlets = client.copy_remote_file(
            remote,
            get_abs_file_path(local, remote) if single_copy else local,
            recurse=True if not single_copy else False
        )
        for greenlet in greenlets:
            yield greenlet


def copy_from_remote(client, local, remotes, single_copy=False):
    greenlets = make_greenlets(client, local, remotes, single_copy=single_copy)
    joinall(list(greenlets), raise_error=True)


def get_abs_file_path(local, remote):
    """Return the abs file path to the downloaded file. """
    return os.path.abspath(os.path.join(local, remote.split('/')[-1]))
