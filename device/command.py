import os
import sys
from collections import namedtuple
from configparser import ConfigParser, NoSectionError

import click
from logbook import Logger, StreamHandler
from pssh.exceptions import (AuthenticationException, ConnectionErrorException,
                             SSHException)
from workflow_common.helper import get_config_file, load, riser_config_dir
from device.device import (copy_from_remote, get_pssh_client,
                           has_file_extension, process_hosts,
                           get_config_value)

StreamHandler(sys.stdout).push_application()
logger = Logger(__name__)

Prompt = namedtuple('Prompt', ['name', 'type'])
PROMPTS = (
    Prompt(name='hosts', type=click.STRING),
    Prompt(name='port', type=click.INT),
    Prompt(name='private_key', type=click.Path(exists=True)),
    Prompt(name='remote', type=click.STRING),
    Prompt(name='local', type=click.Path(exists=True))
)


@click.group()
@click.pass_context
def device(ctx):
    """Folder sync tool from specified device."""


@device.command('configure')
@click.pass_context
def configure(ctx):
    device = click.prompt('Enter a name for this device', type=click.STRING)
    section_name = f'remote {device}'
    try:
        config = load(get_config_file())
        logger.info('Found existing config file')
    except FileNotFoundError:
        logger.warning('Config file not found. Creating...')
        config = ConfigParser()
        config.add_section(section_name)
    finally:
        sections = [sec.startswith(section_name) for sec in config.sections()]
        if not any(sections):
            config.add_section(section_name)

        for prompt in PROMPTS:
            value = get_config_value(
                config,
                section_name,
                prompt.name,
                prompt_type=prompt.type
            )
            config.set(section_name, prompt.name, str(value))

    with open(os.path.join(riser_config_dir(), 'config'), 'w+') as f:
        config.write(f)

    ctx.obj['device_config'] = config
    logger.debug('Device configured')


@device.command('pull')
@click.option('-k', '--private-key', type=click.Path(exists=True))
@click.option('-p', '--port', type=click.INT)
@click.option('-h', '--hosts', type=click.STRING, multiple=True)
@click.option('-l', '--local', type=click.Path())
@click.option('-r', '--remotes', type=click.STRING)
@click.option('-d', '--device', type=click.STRING)
@click.pass_context
def pull(ctx, device, remotes, local, hosts, port, private_key):
    # Get current config and overwrite if necessary.
    config = load(get_config_file())

    try:
        logger.debug('Trying to get config for device')
        section = f'remote {device}'
        local = config.get(section, 'local') if local is None else local

        if not local.endswith('/'):
            local = local + '/'

        if not any(hosts):
            hosts = process_hosts(config.get(section, 'hosts'))

        port = int(config.get(section, 'port')) if port is None else int(port)
        remotes = config.get(section, 'remote') if remotes is None else remotes
        key = config.get(
            section, 'private_key') if private_key is None else private_key
    except (KeyError, NoSectionError) as exc:
        logger.warning(f'No config section for {exc.args}')
        click.echo('No config found. Please run `riser device configure`')
        sys.exit(0)

    try:
        if len(remotes) > 1:
            single_copy = False
        else:
            single_copy = has_file_extension(remotes)
        client = get_pssh_client(
            hosts,
            key,
            port=port,
            single_copy=single_copy
        )
    except AuthenticationException:
        logger.exception('Could not authenticate to remote server')
    except SSHException:
        logger.exception('Could not authenticate to the SSH server')
    except ConnectionErrorException:
        logger.exception('Connection refused')
    else:
        try:
            copy_from_remote(client, local, remotes, single_copy=single_copy)
        except FileNotFoundError:
            logger.exception('Remote file not found.')
            sys.exit(0)


device.add_command(pull)
device.add_command(configure)
