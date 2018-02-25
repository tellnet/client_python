#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) owned by Pablo Fernandez Fernandez
# All rights reserved (including reproduce, distribute or create derivatives,
#  unless explicitly granted otherwise)

# Changelog
#
# v0.4 - 2018-02-25 - Pablo Fernandez
#  - Prep for public release, licensed
#  - Moved config to a file
#
# v0.3 - 2018-02-18 - Pablo Fernandez
#  - New parameters --alias and --debug
#  - New commands network update, member update and member list
#
# v0.2 - 2018-02-10 - Pablo Fernandez
#  - First functional version with parameters
#  - Share link with QR code
#
# v0.1 - 2018-01-21 - Pablo Fernandez
#  - Add networs, members, messages in Dummy mode
#  - Get messages

# Libs
import requests
import argparse
import os, sys
import json
import qrcode

# Vars
networks_file = os.path.expanduser('~/.tellnet/networks.json')
config_file = os.path.expanduser('~/.tellnet/config.json')

# Params
parser = argparse.ArgumentParser(description='Tellnet.io python client', formatter_class=argparse.RawTextHelpFormatter,
                                 epilog="Typical steps:\n  1) "+sys.argv[0]+" network create --share\n  2) "+
                                        sys.argv[0]+" message create Hello There!"   )
parser.add_argument('component', metavar='<component>', choices=["network","member","message"],
                    type=str, help='What component to interact [network|member|message]')
parser.add_argument('action', metavar='<action>', choices=["create","list","update","delete"], type=str,
                    help='Action to perform on the component [create|list]')
parser.add_argument('--share', action='store_true',
                    help='Combine network create with member create, to share a \nnewly created network')
parser.add_argument('--network', help='Perform the action on this network')
parser.add_argument('--alias', help="Set the alias for either a network or a member")
parser.add_argument('--debug', help='Print input and output of each request', action="store_true")
#parser.add_argument('--show-alias', help='Print also the alias for the member on each message', action="store_true")

args, unknownargs = parser.parse_known_args()


def load_from_file(file, default):
  try:
    with open(file, 'r') as handle:
      return json.load(handle)
  except:
    return default

def gen_config_file(filename):
  config = {'endpoint': 'http://localhost:1234/v0/', 'new_network_auth': {'username': 'guest', 'password': 'abc123'} }
  if not os.path.exists(os.path.dirname(filename)):
    os.makedirs(os.path.dirname(filename))
  try:
    with open(filename, 'w+') as file:
      file.write(json.dumps(config, indent=2))  # use `json.loads` to do the reverse
  except:
    print("Error writing file %s" % filename)


# Writes the new network as the first in the list (default)
def store_networks():
  filename = networks_file
  if not os.path.exists(os.path.dirname(filename)):
    os.makedirs(os.path.dirname(filename))
  try:
    with open(filename, 'w+') as file:
      file.write(json.dumps(networks, indent=2))  # use `json.loads` to do the reverse
  except:
    print("Error writing file %s" % filename)

def select_network():
  if len(networks) == 0:
    print("No networks available, please create one first")
    exit(1)
  if args.network:
    # find the network in our list
    index = next((index for (index, d) in enumerate(networks) if d["network_id"] == args.network), None)
    if index == None:
      print("Error, network %s not found" % args.network)
      exit(1)
    if index != 0:
      # Make it the default and return it (switch it with index 0)
      networks[index], networks[0] = networks[0], networks[index]
      store_networks()
  # return the first one
  return networks[0]

def check_error(r):
  if args.debug:
    print("REQUEST %s" %r.request.method, r.url)
    print("REQUEST HEADERS: ", r.request.headers)
    print("REQUEST BODY: ", r.request.body)
    print("RESPONSE BODY: ", r.text)

  if not r.ok:
    print("Error %i" %  r.status_code)
    print(r.text)
    exit(1)



# ******** BEGIN *********

# Prepare config
config = load_from_file(config_file, {})
if 'endpoint' not in config:
  gen_config_file(config_file)
  config = load_from_file(config_file, {})
# some servers may require it (and some may not)
new_network_auth = (config['new_network_auth']['username'], config['new_network_auth']['password']) if 'new_network_auth' in config else None
endpoint = config['endpoint']  # force fail if does not exist

# Load existing networks
networks = load_from_file(networks_file, [])


create_network_and_share = False  # for later

if args.component == 'network' and args.action == 'create':
  alias = args.alias
  data = {'type': 'home', 'alias': alias}  # complete
  r = requests.post(endpoint + 'network', json=data, auth=new_network_auth)
  check_error(r)
  out = r.json()["member"]
  print("Created network %s" % out["network_id"])
  network = {'endpoint': endpoint, 'network_id': out["network_id"], 'member_id': out["id"], 'member_secret': out["secret"], 'alias': alias}
  networks.insert(0, network)
  store_networks()
  if args.share:
    create_network_and_share = True

if args.component == 'network' and args.action == 'list':
  first = True
  for n in networks:
    extra = "(DEFAULT)" if first else ""
    first = False
    print("%s @ %s %s" % (n["network_id"], n["endpoint"], extra))

if args.component == 'network' and args.action == 'update':
  net = select_network()
  if args.alias == None:
    print "Error: alias missing"
    exit(1)
  data = {'alias': args.alias}
  r = requests.post(net["endpoint"]+net["network_id"]+'/network', json = data,
                    auth=(net["member_id"], net["member_secret"]) )
  check_error(r)
  net['alias'] = args.alias
  networks[0] = net # replace the first element with updated info (must be the first!)
  store_networks()
  out = r.json()
  print("Network %s, status:%s, type:%s, alias:%s" % (out["id"], out["status"], out["type"], out["alias"]))

if args.component == 'message' and args.action == 'create':
  if len(unknownargs) == 0:
    print("No message to send!")
    exit (1)
  message = " ".join(unknownargs)
  net = select_network()
  data = {"message": message}
  r = requests.post(net["endpoint"]+net["network_id"]+'/message', json = data,
                    auth=(net["member_id"], net["member_secret"]) )
  check_error(r)
  print("Message sent to %s" % net["network_id"])

if args.component == 'message' and args.action == 'list':
  net = select_network()
  data = { "limit": 10 }
  r = requests.get(net["endpoint"]+net["network_id"]+'/message', params = data,
                   auth=(net["member_id"], net["member_secret"]) )
  check_error(r)
  out = r.json()
  print("Network: %s" % out["network_id"])
  for m in out["messages"]:
    print("@%s: %s" % (m["sender_id"], m["message"]))


if create_network_and_share or (args.component == 'member' and args.action == 'create'):
  net = select_network()
  data = {"role":"admin", "alias": args.alias}
  r = requests.post(net["endpoint"]+net["network_id"]+'/member', json = data,
                    auth=(net["member_id"], net["member_secret"]) )
  check_error(r)
  out = r.json()
  share_string = net["endpoint"].split("://")[0] + "://" +\
                 out["id"] + ":" + out["secret"] + "@" + \
                 net["endpoint"].split("://")[1] +\
                 net["network_id"] + '/'
  print("Share this link:")
  print(share_string)
  qr = qrcode.QRCode()
  qr.add_data(share_string)
  qr.print_ascii(invert=True)

if args.component == 'member' and args.action == 'update':
  net = select_network()
  if args.alias == None:
    print "Error: alias missing"
    exit(1)
  # For now we can only change our own alias (not the alias of others)
  data = {"alias": args.alias}
  r = requests.post(net["endpoint"] + net["network_id"] + '/member/' + net["member_id"], json=data,
                    auth=(net["member_id"], net["member_secret"]))
  check_error(r)
  out = r.json()
  print("Member: @%s (%s)" % (out["id"], out["alias"]))

# MISSING A POSITIONAL PARAMETER TO DEFINE WHO TO DELETE
#if args.component == 'member' and args.action == 'delete':
#  net = select_network()
#  # For now we can only change our own alias (not the alias of others)
#  data = {"alias": args.alias}
#  r = requests.post(net["endpoint"] + net["network_id"] + '/member/' + net["member_id"], json=data,
#                    auth=(net["member_id"], net["member_secret"]))
#  check_error(r)
#  out = r.json()
#  print("Member: @%s (%s)" % (out["id"], out["alias"]))

if args.component == 'member' and args.action == 'list':
  net = select_network()
  r = requests.get(net["endpoint"]+net["network_id"]+'/member',
                    auth=(net["member_id"], net["member_secret"]) )
  check_error(r)
  out = r.json()
  print("Network: %s" % out["network_id"])
  for m in out["members"]:
    me = '(YOU)' if m["id"] == net["member_id"] else '' 
    print("@%s (%s): %s %s" % (m["id"], m["alias"], m["role"], me))
