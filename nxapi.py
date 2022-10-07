#!/usr/bin/env python3
# Nxapi() = nxapi.py
our_version = 100
'''
Name: nxapi.py
Author: Allen Robel
Description: Simple NX-OS cli interaction using nxapi 

Synopsis:

from nxapi import Nxapi

# Example config commands
nx = Nxapi('some_username','some_password','some_ipv4_address')
nx.config_list = ['configure terminal', 'interface Eth1/1', 'description foo']
nx.conf()

# Example show command
nx = Nxapi('some_username','some_password','some_ipv4_address')
nx.timeout = 100
nx.show('show bgp process')
print("result_code: {}".format(nx.result_code))
print("length: {}".format(nx.response_length))
print("output {}".format(nx.print_response))
op = nx.op
nx.print_result_code(rc)


'''

import requests
import json
import urllib3

class Nxapi(object):
    def __init__(self,username,password,dut):
        self.debug_enable = False # set to True to print debug info
        self.error_enable = True # set to True to print error info
        self.info_enable = True # set to True to print fyi info
        self.lib_version = our_version
        self.lib_name = 'Nxapi'
        self.log_prefix = '{}_v{}'.format(self.lib_name, self.lib_version)

        self._https_server_port = 443
        self.properties = dict()
        self.properties['config_list'] = None
        self._timeout = 1200
        self.username = username
        self.password = password
        self._dut     = dut
        self.valid_output_formats = ['dict','json']
        self._hostname = None
        self.cli = None
        self.cookies = dict()
        self._cookie_file = '/tmp/{}.cookies'.format(self._dut)
        self._process_cookies = True
        self._save_cookies = True
        self.session = requests.Session()
        self.session.trust_env = False

        self.na_bool  = False
        self.na_str = 'na'
        self.na_int = -1
        self.result_codes = list()
        self.body = [] # set in _verify_body(), a list of bodies from responses
        self.RC_HUH_WTF = self.na_int
        self.RC_200_SUCCESS = 200
        self.RC_400_CLI_ERROR = 400
        self.RC_413_REQUEST_TOO_LARGE = 413
        self.RC_500_INTERNAL_ERROR = 500
        self.RC_501_STRUCTURED_OUTPUT_NOT_SUPPORTED = 501
        self.RC_SUCCESS_BUT_OUTPUT_LEN_ZERO = 99200
        self.RC_JSON_RPC = 99300
        self.RC_RESULT_VALUE_IS_NONE = 99993
        self.RC_OUTPUTS_KEY_NOT_PRESENT_IN_OUTPUT = 99994
        self.RC_INS_API_KEY_NOT_PRESENT_IN_OUTPUT = 99995
        self.RC_BODY_KEY_NOT_PRESENT_IN_OUTPUT = 99996
        self.RC_RESULT_KEY_NOT_PRESENT_IN_OUTPUT = 99997
        self.RC_NOT_RETURNED_BY_DEVICE = 99998
        self.RC_NOT_INTEGER = 99999
        self.PAYLOAD_JSON = 'json'
        self.PAYLOAD_JSON_RPC = 'json-rpc'
        self.rc_dict = dict()
        self.rc_dict[self.RC_JSON_RPC] = 'json-rpc content-type does not return a result code'
        self.rc_dict[self.RC_200_SUCCESS] = 'Success'
        self.rc_dict[self.RC_HUH_WTF] = 'Huh?'
        self.rc_dict[self.RC_400_CLI_ERROR] = 'Error code 400 - CLI Error'
        self.rc_dict[self.RC_500_INTERNAL_ERROR] = 'Error code 500 - Internal Server Error'
        self.rc_dict[self.RC_413_REQUEST_TOO_LARGE] = 'Error code 413 - Request is too large'
        self.rc_dict[self.RC_RESULT_VALUE_IS_NONE] = 'result key is present, but has the value None'
        self.rc_dict[self.RC_501_STRUCTURED_OUTPUT_NOT_SUPPORTED] = 'Error code 501 - Structured output not supported'
        self.rc_dict[self.RC_SUCCESS_BUT_OUTPUT_LEN_ZERO] = 'Success, but output was zero bytes'
        self.rc_dict[self.RC_NOT_INTEGER] = 'Result code not parseable as integer'
        self.rc_dict[self.RC_NOT_RETURNED_BY_DEVICE] = 'Result code not returned by device'
        self.rc_dict[self.RC_OUTPUTS_KEY_NOT_PRESENT_IN_OUTPUT] = '[outputs] key not present in output'
        self.rc_dict[self.RC_INS_API_KEY_NOT_PRESENT_IN_OUTPUT] = '[ins-api] key not present in output'
        self.rc_dict[self.RC_RESULT_KEY_NOT_PRESENT_IN_OUTPUT] = '[result] key not present in output'
        self.rc_dict[self.RC_BODY_KEY_NOT_PRESENT_IN_OUTPUT] = '[result][body] keys not present in output'
        # will always be an integer, regardless of what is returned by the device
        self._result_code = self.na_int
        self._request_id = self.na_int
        self._result_msg = self.na_str
        self._length = 0
        self.proxies = dict()

        self.op = dict()

    def print_debug(self,x):
        if self.debug_enable == True:
            print("DEBUG: {}".format(x))
    def print_error(self,x):
        if self.error_enable == True:
            print("ERROR: {}".format(x))
    def print_info(self,x):
        if self.info_enable == True:
            print("INFO: {}".format(x))
    
    def is_boolean(self,x):
        '''verify x is a boolean value'''
        if type(x) != type(True):
            return False
        return True

    def add_proxy(self, scheme, url):
        if scheme not in ['http', 'https']:
            self.print_error('exiting. unrecognized proxy scheme {}.  Expected one of http or https')
            exit(1)
        self.proxies[scheme] = url

    def clear_proxies(self):
        self.proxies = dict()

    @property
    def hostname(self):
        return self._hostname
    @hostname.setter
    def hostname(self, x):
        self._hostname = x
    
    @property
    def https_server_port(self):
        return self._https_server_port
    @https_server_port.setter
    def https_server_port(self, x):
        '''
        call this prior to calling nxapi_init() to set a non-default server port
        '''
        try:
            x = int(str(x))
        except:
            self.print_error('exiting. expected int() for https_server_port. Got {}.'.format(x))
            exit(1)
        self._https_server_port = x

    @property
    def config_list(self):
        return self.properties['config_list']
    @config_list.setter
    def config_list(self, x):
        self.properties['config_list'] = x
    @property
    def dut(self):
        return self._dut
    @dut.setter
    def dut(self, x):
        '''
        call this prior to calling nxapi_init() to change dut
        '''
        self._dut = x

    def nxapi_init(self, argparse_instance=None):
        '''
        Use this from scripts to configure various cookie and urllib preferences

        Takes an argparse instance and uses any settings in that.

        Example:

        <argparse code removed for brevity>
        default.add_argument('--disable_urllib_warnings',
                            dest='disable_urllib_warnings',
                            required=False,
                            action='store_true',
                            default=False,
                            help='(default: %(default)s) ' + help_disable_urllib_warnings + ex_disable_urllib_warnings)

        cfg = parser.parse_args()

        nx = Nxapi(cfg.username, cfg.password, cfg.ip)
        nx.config_list = re.split(',', cfg.cmd)
        nx.nxapi_init(cfg) # passes the argparse instance to Nxapi, for e.g. disable_urllib_warnings, etc
        nx.conf()


        if argparse_instance is not provided, cookies will be used by default
        '''
        if argparse_instance != None:
            self.set_cookie_prefs(argparse_instance)
            self.set_urllib_prefs(argparse_instance)
        self.load_cookies()
        self.get_hostname()

    def get_hostname(self):
        _method_name = 'get_hostname'
        self.show('show hostname')
        try:
            self.hostname = self.op['ins_api']['outputs']['output']['body']['hostname']
        except:
            self.print_warning('{}.{}() setting hostname to None. self.op = {}'.format(self.lib_name, _method_name, self.op))
            self.hostname = None

    def log_debug(self):
        self.print_debug('{} {} result_code {} -> {}'.format(
                                            self.lib_name,
                                            self.hostname,
                                            self.result_code,
                                            self.rc_dict[self.result_code]
                                            ))

    def log_error(self):
        self.print_error('{} {} result_code {} -> {}'.format(
                                            self.lib_name,
                                            self.hostname,
                                            self.result_code,
                                            self.rc_dict[self.result_code]
                                            ))
    def log_warning(self):
        self.print_warning('{} {} result_code {} -> {}'.format(
                                            self.lib_name,
                                            self.hostname,
                                            self.result_code,
                                            self.rc_dict[self.result_code]
                                            ))

    def _verify_body(self):
        '''
        used for verification of jsonrpc responses
        '''
        if self.payload_type == self.PAYLOAD_JSON:
            return
        self.print_debug('{} _verify_body: self.op {}'.format(self.lib_name, self.op))
        if 'result' not in self.op:
            self.result_code = self.RC_RESULT_KEY_NOT_PRESENT_IN_OUTPUT
            self.log_error()
            exit(1)
        if self.op['result'] == None:
            self.result_code = self.RC_RESULT_VALUE_IS_NONE
            self.log_warning()
            self.print_warning("{} {} Setting body to null dictionary to avoid exit due to body not present.  Good luck, you're on your own.".format(
                              self.lib_name,
                              self.hostname))
            self.op['result'] = {'body': {}, 'id': 1}
        if 'body' not in self.op['result']:
            self.result_code = self.RC_BODY_KEY_NOT_PRESENT_IN_OUTPUT
            self.log_error()
            exit(1)
        # TODO - check if jsonrpc also returns a list of bodies if multi-response (similar to ins_api)
        self.body = self.op['result']['body']
        return len('{}'.format(self.op['result']['body']))

    def _verify_outputs(self):
        _method_name = '_verify_outputs'
        if self.payload_type != self.PAYLOAD_JSON:
            self.print_warning('{}.{}: Returning with noop. Inappropriate payload_type {}. Expected {}.'.format(
                    self.lib_name,
                    _method_name,
                    self.payload_type,
                    self.PAYLOAD_JSON))
            return
        self.print_debug('{}.{}: self.op {}'.format(self.lib_name, _method_name, self.op))
        if "ins_api" not in self.op:
            self.result_code = self.RC_INS_API_KEY_NOT_PRESENT_IN_OUTPUT
            self.log_error()
            exit(1)
        elif 'outputs' not in self.op['ins_api']:
            self.result_code = self.RC_OUTPUTS_KEY_NOT_PRESENT_IN_OUTPUT
            self.log_error
            exit(1)
        return len('{}'.format(self.op['ins_api']['outputs']))

    def set_response_length(self,op):
        if self.payload_type == self.PAYLOAD_JSON_RPC:
            self.set_response_length_show(op)
        elif self.payload_type == self.PAYLOAD_JSON:
            self.set_response_length_conf(op)

    def set_response_length_show(self, op):
        self.response_length = self._verify_body()

    def set_response_length_conf(self, op):
        self.response_length = self._verify_outputs()

    def print_response(self):
        self.print_debug('{}'.format(json.dumps(self.op, indent=4, sort_keys=True)))

    def print_result_code(self, rc):
        if rc in self.rc_dict:
            self.print_debug('{} {} result_code {} -> {}'.format(self.lib_name, self.hostname, self.result_code, self.rc_dict[self.result_code]))
        else:
            self.print_debug('{} Unknown result_code {}'.format(self.lib_name, rc))

    def _parse_code(self,d):

        if self.payload_type == self.PAYLOAD_JSON_RPC:
            self.result_code = self.RC_JSON_RPC
            return
        if 'code' not in d:
            self.result_code = self.RC_NOT_RETURNED_BY_DEVICE
            return

        try:
            self.result_msg = d['msg']
        except:
            self.print_warning('{} {} response contains no msg {}'.format(self.lib_name, self.hostname, d))

        try:
            self.result_code = int(d['code'])
            self.print_debug('{} _parse_code: result_code {}'.format(self.lib_name, self.result_code))
        except:
            self.result_code = self.RC_NOT_INTEGER
            self.log_debug()
            return
        if self.result_code != 200:
            if self.result_code in self.rc_dict:
                self.log_debug()
                self.print_debug('{} {} msg (if any) returned was {}'.format(
                        self.lib_name,
                        self.dut,
                        self.result_msg))

            else:
                self.print_debug('{} {} code != 200. Got {}.'.format(
                        self.lib_name,
                        self.dut,
                        self.result_code))
                self.print_info('{} Please let arobel@cisco.com know that code {} needs to be added to self.rc_dict.  Thanks!'.format(
                        self.lib_name,
                        self.result_code))
        self.result_codes.append(self.result_code)

    def _verify_show_response_jsonrpc(self):
        '''
        log appropriate error if 'show' content does not contain expected content
        should be used to verify jsonrpc type requests
        '''
        self._verify_body()
        if 'id' in self.op:
            self.request_id = int(self.op['id'])
        self.result_code = self.RC_JSON_RPC

    def _append_body(self,d):
        '''
        HTTP spec allows for a body to be present, or not.
        https://stackoverflow.com/questions/8628725/comprehensive-list-of-http-status-codes-that-dont-include-a-response-body
        We also may have multiple responses.
        This method appends to self.body an empty dict if no body is present, or the body if a body is present.
        It's up to the caller to ensure that self.body has been initialized to an empty list.
        '''
        _method_name = '_append_body'
        if 'body' not in d:
            self.body.append(dict())
        else:
            self.body.append(d['body'])

    def _verify_ins_api_response(self):
        '''
        log appropriate error if 'show' content does not contain expected content
        should be used to verify ins_api type requests

        This also populates the list nxapi.body via self._append_body()
        '''
        # self.result_codes is appended to in self._parse()
        _method_name = '_verify_ins_api_response'
        self.result_codes = list()
        self._verify_outputs()
        self.print_debug('{}.{}: {} Got self.op {}'.format(
                self.lib_name,
                _method_name,
                self.dut,
                self.op))
        if 'output' not in self.op['ins_api']['outputs']:
            self.print_error('{}.{}: {} Exiting. Response does not contain [ins_api][outputs][output] key'.format(
                self.lib_name,
                _method_name,
                self.dut))
            exit(1)
        self.body = list()
        if type(self.op['ins_api']['outputs']['output']) == type(dict()):
            self._append_body(self.op['ins_api']['outputs']['output'])
            self._parse_code(self.op['ins_api']['outputs']['output'])
        if type(self.op['ins_api']['outputs']['output']) == type(list()):
            for d in self.op['ins_api']['outputs']['output']:
                self._append_body(d)
                self._parse_code(d)

    def _send_nxapi(self):
        _method_name = '_send_nxapi'
        headers={'content-type':'application/{}'.format(self.payload_type)}
        try:
            self.print_debug('POST with self.cookies {}'.format(self.cookies))
            self.url = 'https://{}:{}/ins'.format(self.dut, self.https_server_port)

            self.response = self.session.post(
                                                self.url,
                                                auth=(self.username, self.password),
                                                data=json.dumps(self.payload),
                                                proxies=self.proxies,
                                                headers=headers,
                                                timeout=self.timeout,
                                                verify=False,
                                                cookies=self.cookies
                                             )

        except urllib3.exceptions.NewConnectionError as e:
            self.print_warning('{}.{}: NewConnectionError -> unable to connect to {}. Error: {}'.format(
                self.lib_name,
                _method_name,
                self.dut, e))
            return
        except Exception as e:
            self.print_warning('{}.{}: GenericException -> unable to connect to {}. Error: {}'.format(
                self.lib_name,
                _method_name,
                self.dut, e))
            return

        if self.response.status_code != 200:
            msg = "{}.{}: {} call failed. Code {} ({})".format(
                            self.lib_name,
                            _method_name,
                            self.dut,
                            self.response.status_code,
                            self.response.content.decode("utf-8"))
            self.print_error(msg)
            exit(1)
            #raise Exception(msg)
        self.print_debug('{}.{}: self.response {}'.format(
            self.lib_name,
            _method_name,
            self.response))
        try:
            self.op = self.response.json()
        except Exception as e:
            self.print_warning("{}.{}: Got exception while converting response to JSON. Exception: {}".format(
                self.lib_name,
                _method_name,
                e))
            return
        if self.payload_type == self.PAYLOAD_JSON:
            self.print_debug('{}.{}: verifying payload with self._verify_ins_api_response()'.format(
                self.lib_name,
                _method_name))
            self._verify_ins_api_response()
        elif self.payload_type == self.PAYLOAD_JSON_RPC:
            self.print_debug('{}.{}: verifying payload with self._verify_show_response_jsonrpc()'.format(
                self.lib_name,
                _method_name))
            self._verify_show_response_jsonrpc()
        else:
            self.print_error('{}.{}: {} Exiting. Unknown payload_type {}'.format(
                self.lib_name,
                _method_name,
                self.hostname,
                self.payload_type))
            exit(1)
        self.print_debug("{}.{}: {} self.payload {}".format(
            self.lib_name,
            _method_name,
            self.dut,
            self.payload))
        self.print_debug("{}.{}: {} output {}".format(
                self.lib_name,
                _method_name,
                self.dut,
                json.dumps(self.op,
                           indent=4,
                           sort_keys=True)))
        self.set_response_length(self.op)
        self.reconcile_cookies()

        self.print_debug("{}.{}: Got self.op {}".format(
            self.lib_name,
            _method_name,
            self.op))

    def reconcile_cookies(self):
        if self.process_cookies == False:
            return
        if len(self.response.cookies) == 0:
            self.print_debug('old cookies are fresh')
            return
        if self.response.cookies != self.cookies:
            self.print_debug('old cookies {}'.format(self.cookies))
            self.print_debug('new cookies {}'.format(self.response.cookies))
            self.print_debug('cookies refreshed by DUT')
            self.cookies = self.response.cookies
            self.save_cookie_file()

    def save_cookie_file(self):
        if self.save_cookies == False:
            return
        d = self.session.cookies.get_dict()
        with open(self.cookie_file, 'w') as fh:
            json.dump(d, fh)

    def load_cookies(self):
        if self.process_cookies == False:
            return
        try:
            with open(self.cookie_file, 'r') as fh:
                self.cookies = requests.utils.cookiejar_from_dict(json.load(fh))
                self.print_debug('load cookies: {}'.format(self.cookies))
        except:
            self.print_debug('Could not read cookie_file {}'.format(self.cookie_file))
            return dict()

    def show_jsonrpc(self,_cmd=None):
        '''
        show_jsonrpc() is an alternative user-facing method for issuing show cli and getting response

        See also: show() which uses NXAPI (ins_api) and is the preferred method.

        If no command is passed to show_jsonrpc, self.cli will be used.
        Else, the passed command will be used
        '''
        _method_name = 'show_jsonrpc'
        if _cmd == None:
            _cmd = self.cli
        if _cmd == None:
            self.print_error('Exiting. Please set self.cli first, or pass command to instance.show_jsonrpc()')
            exit(1)
        if type(_cmd) != type(str()):
            self.print_error('{}.{}: Exiting. _cmd must be type str(). Got: type {} cmd {}.'.format(
                self.lib_name,
                _method_name,
                type(_cmd),
                _cmd))
            exit(1)
        self.payload = [
            {
                "jsonrpc": "2.0",
                "method": "cli",
                "params": {
                    "cmd": _cmd,
                    "version": 1.2
                },
                "id": 1
            }
        ]
        self.payload_type = self.PAYLOAD_JSON_RPC
        self._send_nxapi()

    def show(self,_cmd=None):
        '''
        show() is the main user-facing method for issuing show cli and getting response using ins_api

        See also: show_jsonrpc() which using JSON_RPC method

        If no command is passed to show, self.cli will be used.
        Else, the passed command will be used
        '''
        _method_name = 'show'
        if _cmd == None:
            _cmd = self.cli
        if _cmd == None:
            self.print_error('Exiting. Please set self.cli first, or pass command to instance.show()')
            exit(1)
        if type(_cmd) != type(str()):
            self.print_error('{}.{}: Exiting. _cmd must be type str(). Got: type {} for _cmd {}'.format(
                self.lib_name,
                _method_name,
                type(_cmd),
                _cmd))
            exit(1)
        self.payload = {
            "ins_api": {
                "version": "1.0",
                "type": "cli_show",
                "chunk": "0",       # do not chunk results
                "sid": "1",         # session ID
                "input": _cmd,
                "output_format": "json"
            }
        }
        self.payload_type = self.PAYLOAD_JSON
        self.print_debug('sending nxapi for _cmd {}.  Payload {}'.format(_cmd, self.payload))
        self._send_nxapi()

    def conf(self):
        '''
        conf() is the main user-facing method for issuing configuration cli and getting response(s)

        conf() expects self.config_list to be set with a python list of NXOS config commands.
        '''
        commands = list()
        if self.config_list != None:
            self.print_debug('{} Processing self.config_list'.format(self.lib_name))
            commands = self.config_list
        if type(commands) != type(list()):
            self.print_error('{} Early return. Expected python list. Got: {}'.format(self.lib_name, commands))
            return
        if not len(commands) > 0:
            self.print_error('{} Early return. commands list must be > 0. Got: {}'.format(self.lib_name, commands))
            return
        element_num = 0
        for cli in commands:
            if type(cli) != type(str()):
                self.print_error('{} Skipping command. Not str(). commands element {} type {}: {}.'.format(self.lib_name, element_num, type(cli), cli))
                continue
            element_num += 1

        _input = ' ; '.join(commands)

        self.print_debug('{} sending {}'.format(self.lib_name, _input))
        self.payload = {
            "ins_api": {
                "version": "1.0",
                "type": "cli_conf",
                "chunk": "0",       # do not chunk results
                "sid": "1",         # session ID
                "input": _input,
                "output_format": "json"
            }
        }
        self.payload_type = self.PAYLOAD_JSON
        self._send_nxapi()

    def str_to_boolean(self, _x):
        '''
        if _x is a str() == to 'True', 'true', 'TRUE', 'False', 'false', 'FALSE' etc, return a boolean
        else, return string
        '''
        if str(_x).lower() == 'false':
            return False
        if str(_x).lower() == 'true':
            return True
        return _x

    @property
    def body_length(self):
        return len(self.body)

    @property
    def response_length(self):
        return self._response_length
    @response_length.setter
    def response_length(self, _x):
        try:
            self._response_length = int(_x)
        except:
            self.print_error('{} {} length is not an integer: {}'.format(self.lib_name, self.hostname, _x))

    def set_urllib_prefs(self, argparse_instance=None):
        '''
        given argparse_instance, set urllib prefs based on the value of instance.disable_urllib_warnings
        '''
        try:
            _disable_urllib_warnings = argparse_instance.disable_urllib_warnings
        except:
            pass
        try:
            if _disable_urllib_warnings == True:
                self.print_debug('Disabling urllib3 warnings')
                urllib3.warnings.filterwarnings('ignore', module='urllib3')
            elif _disable_urllib_warnings == False:
                self.print_debug('Enabling/Resetting urllib3 warnings')
                urllib3.warnings.filterwarnings('default', module='urllib3')
            else:
                self.print_debug('Enabling/Resetting urllib3 warnings')
                urllib3.warnings.filterwarnings('default', module='urllib3')
        except:
            self.print_warning('Unable to modify urllib3 warning behavior. Likely urllib3 is out of date.')
            try:
                self.print_warning('urllib3 version {}'.format(urllib3.__version__))
            except:
                pass
            return

    def set_cookie_prefs(self, argparse_instance):
        '''
        given argparse_instance, set cookie prefs
        '''
        self.save_cookies = argparse_instance.save_cookies
        self.process_cookies = argparse_instance.process_cookies
        if argparse_instance.cookie_file != None:
            self.cookie_file = argparse_instance.cookie_file
            self.print_debug('{} set self.cookie_file to {}'.format(self.lib_name, self.cookie_file))

    @property
    def process_cookies(self):
        return self._process_cookies
    @process_cookies.setter
    def process_cookies(self, _x):
        _x = self.str_to_boolean(_x)
        if not self.is_boolean(_x):
            self.print_error('Exiting. Expected boolean for process_cookies, got {}'.format(_x))
            exit(1)
        self._process_cookies = _x

    @property
    def save_cookies(self):
        return self._save_cookies
    @save_cookies.setter
    def save_cookies(self, _x):
        _x = self.str_to_boolean(_x)
        if not self.is_boolean(_x):
            self.print_error('Exiting. Expected boolean for save_cookies, got {}'.format(_x))
            exit(1)
        self._save_cookies = _x

    @property
    def cookie_file(self):
        return self._cookie_file
    @cookie_file.setter
    def cookie_file(self, _x):
        self._cookie_file = _x


    @property
    def timeout(self):
        return self._timeout
    @timeout.setter
    def timeout(self, _x):
        try:
            self._timeout = int(_x)
        except:
            self.print_error('{} {} Exiting. Timeout is not an integer: {}'.format(self.lib_name, self.hostname, _x))
            exit(1)

    @property
    def request_id(self):
        return self._request_id
    @request_id.setter
    def request_id(self, _x):
        try:
            self._request_id = int(_x)
        except:
            self.print_error('{} {} request_id is not an integer: {}'.format(self.lib_name, self.hostname, _x))

    @property
    def result_code(self):
        return self._result_code
    @result_code.setter
    def result_code(self, _x):
        try:
            self._result_code = int(_x)
        except:
            self.print_error('{} {} result_code is not an integer: {}'.format(self.lib_name, self.hostname, _x))

    @property
    def result_msg(self):
        return self._result_msg
    @result_msg.setter
    def result_msg(self, _x):
        self._result_msg = _x

    @property
    def conf_results(self):
        return self.result_codes
