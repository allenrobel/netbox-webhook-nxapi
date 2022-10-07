#!/usr/bin/env python3
'''
Name: nxapi_config.py
Author: Allen Robel
Description: Configure Nexus switches via NXAPI
Usage example:

./nxapi_config.py --disable_urllib_warnings --username admin --password mypassword --ip 192.168.1.1 --cmd 'config term,interface eth1/1,description foo'

'''
our_version = 100

# standard libraries
import argparse
import re
import sys
# local libraries
from nxapi import Nxapi

title = 'Configure Nexus switch using NXAPI'
parser = argparse.ArgumentParser(description='DESCRIPTION: {}'.format(title))
mandatory = parser.add_argument_group(title='MANDATORY SCRIPT ARGS')
default   = parser.add_argument_group(title='DEFAULT SCRIPT ARGS')

ex_prefix = 'Example: '

# Basic args
help_cmd    = 'Comma-separated list of commands (no spaces) to issue on --ip'
help_silent = 'whether to display the output of show command specified in --cmd'

ex_cmd    = '{} {}'.format(ex_prefix,'--cmd "config term,interface eth1/1,description foobar"')
ex_silent = '{} {}'.format(ex_prefix,'--silent')

mandatory.add_argument('--cmd',
                       dest='cmd',
                       required=True,
                       help ='{} {}'.format(help_cmd,ex_cmd))
default.add_argument('--silent',
                     dest     = 'silent',
                     required = False,
                     action   = 'store_true',
                     default  = False,
                     help     = '{} {}'.format(help_silent,ex_silent))

# Cookie args
help_save_cookies = 'NXAPI only, If present, save cookies.'
help_process_cookies = 'NXAPI only, If present, process cookies for the session(s) within a single script invocation.'
help_cookie_file = 'NXAPI only, specifies filname for saving cookies.'
help_disable_urllib_warnings = 'NXAPI only, if present, disable urllib3 warnings about insecure connections'

ex_save_cookies = '{} --save_cookies'.format(ex_prefix)
ex_process_cookies = '{} --process_cookies'.format(ex_prefix)
ex_cookie_file = '{} --cookie_file /tmp/my_cookie_file'.format(ex_prefix)
ex_disable_urllib_warnings = '{} --disable_urllib_warnings'.format(ex_prefix)

default.add_argument('--save_cookies',
                     dest='save_cookies',
                     action='store_true',
                     required=False,
                     default=True,
                     help='(default: %(default)s) ' + help_save_cookies + ex_save_cookies)

default.add_argument('--process_cookies',
                     dest='process_cookies',
                     action='store_true',
                     required=False,
                     default=True,
                     help='(default: %(default)s) ' + help_process_cookies + ex_process_cookies)

default.add_argument('--cookie_file',
                     dest='cookie_file',
                     required=False,
                     default=None,
                     help='(default: %(default)s) ' + help_cookie_file + ex_cookie_file)

default.add_argument('--disable_urllib_warnings',
                     dest='disable_urllib_warnings',
                     required=False,
                     action='store_true',
                     default=False,
                     help='(default: %(default)s) ' + help_disable_urllib_warnings + ex_disable_urllib_warnings)


# Connection args

help_ip = 'NX-OS switch ip address/hostname".'
help_username = 'NX-OS switch username.'
help_password = 'NX-OS switch password.'

ex_ip = '{} --ip 10.1.1.1'.format(ex_prefix)
ex_username = '{} --username snoopy'.format(ex_prefix)
ex_password = '{} --password sn0_0p1e'.format(ex_prefix)

mandatory.add_argument('--ip', 
                       dest='ip', 
                       required=True,
                       help=help_ip + ex_ip)

default.add_argument('--username', 
                     dest='username', 
                     default='admin',
                     help='(default: %(default)s) ' + help_username + ex_username)

mandatory.add_argument('--password',
                     dest='password', 
                     help=help_password + ex_password)

parser.add_argument('--version',
                    action='version',
                    version='%(prog)s {}'.format(our_version))
cfg = parser.parse_args()

j = Nxapi(cfg.username, cfg.password, cfg.ip)
j.config_list = re.split(',', cfg.cmd)
j.nxapi_init(cfg) # passes the argparse instance to Nxapi, for e.g. disable_urllib_warnings, etc
j.conf()
