# netbox-webhook-nxapi

This repo provides an example of how one might update NX-OS interfaces using Netbox's webhook feature.

The flow goes something like:

Netbox-->WebhookServer-->update_interface.bash-->nxapi_config.py-->NexusSwitch

In our example, we update the following interface configurations:

- description
- vlan
- mtu
- interface state (shutdown or not)

## Getting started

If you've never used webhooks before, below is a quick-start guide.

### 1. Install [webhook].  If using Ubuntu, and prefer snaps, then:

```bash
sudo snap install webhook
```

else:

```bash
sudo apt install webhook
```

### 2. cd into the directory where you downloaded this repo

### 3. Edit update-interface.bash

Change the following with your NX-OS username and password:

```bash
PASSWORD='your_nxos_password'
USERNAME='admin'
```

### 4. Optionally, update your PYTHONPATH

If you move nxapi.py to a different location, add that location to your PYTHONPATH; either in update-interface.bash, or in your .bash_profile, etc.

### 5. Edit ``hooks.json``

Change ``execute-command`` to point to where ``update-interface.bash`` lives on your server.

``"execute-command": "/home/arobel/netbox-webhook-nxapi/update-interface.bash",``

Change ``command-working-directory`` to this repo's directory on your server.

``"command-working-directory": "/home/arobel/netbox-webhook-nxapi",``

### 6. Start webhook

Specify the port you'll configure Netbox to use (8888 in the below examples)

If using the snap version:

```bash
snap run webhook -hooks hooks.json -port 8888 -verbose
```

Else, if installed using apt:

```bash
webhook -hooks hooks.json -port 8888 --verbose
```

### 7. Configure Netbox

We'll configure Netbox below to trigger a webhook if dcim.interfaces changes

- In the Netbox sidebar, scroll down and click "Other" then "Webhooks"
- Click "Add" in the Webhooks pane.
- For Name* use ``update-interface``
- For Content Types* select ``DCIM > interface`` from the drop-down menu
- Make sure ``Enabled`` is checked.
- Under Events, check ``Creations`` and ``Updates``
- For URL*, use http://your_server:8888/hooks/update-interface

Replace ``your_server`` with the hostname or ip address of your server.
Replace ``8888`` with the port you used in set step 5 above.

- Make sure HTTP Method* is ``POST``
- Make sure HTTP content type* is ``application/json``
- Scroll down to the bottom of the page and click ``Save``

### 8. Update an interface in Netbox

If you do this manually, follow the steps below.  Else, if you'd like to try my [netbox-tools], you can use the ``interface_create_update.py`` script.  Below is an example for that:

```bash
./interface_create_update.py --device cvd_leaf_1 --interface Ethernet1/1 --mode access --type 1000base-x-sfp --vlan 20 --description "DB Servers" --mtu 9216 --disabled
```


- Read the Netbox documentation for adding devices and interfaces if you don't already have a device/interface configured.
- Under ``Devices`` in the Netbox sidebar, select ``Interfaces`` (or select a device and then select its interface from the device interface tab)
- Click the interface to edit (in this case, we are configuring the vlan on access mode interfaces, so select an access interface)
- Make change(s) to the interface (one or more of Description, MTU, Enabled, or Untagged VLAN)
- Click ``Save``

### 9. Check that the webhook fired

Go back to your terminal where you started webhook.  You should see some output that looks similar to:

```bash
[webhook] 2022/10/06 18:34:21 Started POST /hooks/update-interface
[webhook] 2022/10/06 18:34:21 [075319] incoming HTTP request from A.B.C.D:40284
[webhook] 2022/10/06 18:34:21 [075319] update-interface got matched
[webhook] 2022/10/06 18:34:21 [075319] update-interface hook triggered successfully
[webhook] 2022/10/06 18:34:21 Completed 200 OK in 391.854µs
[webhook] 2022/10/06 18:34:21 [075319] executing /home/admin1/arobel/webhooks/update-interface.bash (/home/admin1/arobel/webhooks/update-interface.bash) with arguments ["/home/admin1/arobel/webhooks/update-interface.bash" "cvd_leaf_1" "Ethernet1/1" "10" "Web Servers" "9216" "false"] and environment [] using /home/admin1/arobel/webhooks as cwd
[webhook] 2022/10/06 18:34:26 [075319] command output: 
[webhook] 2022/10/06 18:34:26 [075319] finished handling update-interface
```

### 10. Check the NX-OS switch manually

- Verify the interface configuration changed ``show running-config interface X/Y``
- Verify the accounting log ``show accounting log``


[netbox-tools]: https://github.com/allenrobel/netbox-tools

[webhook]: https://github.com/adnanh/webhook
