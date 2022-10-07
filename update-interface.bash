#!/usr/bin/env bash
# If you move nxapi.py to some other location, add that to your PYTHONPATH
# Either in this script, or e.g. in your bash config, etc.
#export PYTHONPATH="$PYTHONPATH:/path/to/where/you/moved/nxapi.py"
# password for NX-OS switches
PASSWORD='your_nxos_password'
USERNAME='admin'

switch=$1
interface=$2
vlan=$3
description=$4
mtu=$5
enabled=$6

CMD="configure terminal,interface $interface,switchport access vlan $vlan"
if [ ! -z "$description" ]; then
   CMD+=",description $description"
fi
if [ ! -z "$mtu" ]; then
   CMD+=",mtu $mtu"
fi
if [ "$enabled" == false ]; then
   CMD+=",shutdown"
fi
if [ "$enabled" == true ]; then
   CMD+=",no shutdown"
fi
python3 nxapi_config.py --disable_urllib_warnings --username "$USERNAME" --password "$PASSWORD" --ip $switch --cmd "$CMD" > output.log
