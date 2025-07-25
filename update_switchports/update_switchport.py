#! /usr/bin/env python

import csv
import json
import time
import re
import os
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#Define Org and Network
org_name = 'Example Organization'
net_name = 'Main Network'


##Define API key for access to meraki

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-Cisco-Meraki-API-Key": os.environ.get('MERAKI_API_KEY')
}

def get_orgs():
    '''Returns all orgs'''
    url = 'https://api.meraki.com/api/v1/organizations'
    response_code = requests.get(url, headers=headers, verify=False)
    if response_code.status_code == 200:
        orgs = json.loads(response_code.text)
    elif response_code.status_code == 429:
        time.sleep(int(response_code.headers["Retry-After"]))
        response_code = requests.get(url, headers=headers, verify=False)
        orgs = json.loads(response_code.text)
    else:
        print(response_code.text)

    return orgs

def get_networks(organizationId):
    '''Return all networks in a given org'''
    url = f'https://api.meraki.com/api/v1/organizations/{organizationId}/networks'
    response_code = requests.get(url, headers=headers, verify=False)
    if response_code.status_code == 200:
        networks = json.loads(response_code.text)
    elif response_code.status_code == 429:
        time.sleep(int(response_code.headers["Retry-After"]))
        response_code = requests.get(url, headers=headers, verify=False)
        networks = json.loads(response_code.text)
    else:
        print(response_code.text)

    return networks

def get_devices(networkId):
    '''Return all devices in a given network'''
    url = f'https://api.meraki.com/api/v1/networks/{networkId}/devices'
    response_code = requests.get(url, headers=headers, verify=False)
    if response_code.status_code == 200:
        devices = json.loads(response_code.text)
    elif response_code.status_code == 429:
        time.sleep(int(response_code.headers["Retry-After"]))
        response_code = requests.get(url, headers=headers, verify=False)
        devices = json.loads(response_code.text)
    else:
        print(response_code.text)

    return devices

def update_device(serial,port):
    '''Update a device with given serial num'''
    url = f'https://api.meraki.com/api/v1/devices/{serial}/switch/ports/{port["port"]}'
    payload = {
        'name': port['name'],
    }
    response_code = requests.put(url, headers=headers, data=json.dumps(payload),verify=False)
    if response_code.status_code == 200:
        print("Successful update for:",serial, "port:",port["port"])
        return response_code.text
    elif response_code.status_code == 429:
        time.sleep(int(response_code.headers["Retry-After"]))
        response_code = requests.put(url, headers=headers, data=json.dumps(payload),verify=False)
        return response_code.text
    else:
        print("Error code:",response_code.status_code)
        print("Error details:", response_code.text)
        return response_code.status_code

def open_file(filename):
    '''Open a file for reading'''
    raw_file = open(filename, mode = 'r', encoding='utf-8')
    csv_reader = csv.DictReader(raw_file)
    return csv_reader

def open_csv():
    '''Pass raw file through CSV and assign rows/colums to a dictionary'''
    #Define variables
    csv_list = []
    port_list = []
    switch_name = ''
    #prompt user for csv filename
    filename = str(input("Enter the name of the csv file. Include file extension.:\n"))
    #Open CSV
    csv_reader = open_file(filename)
    #Assign CSV to a dict
    for row in csv_reader:
        #print(row)
        if row['Switch'] == switch_name:
            port_dict = {
                'port':row['Port'],
                'name':row['Description'].replace(' ',''),
            }
            port_list.append(port_dict)
        else:
            switch_name = row['Switch']
            port_list = []
            port_dict = {
                'port':row['Port'],
                'name':row['Description'].replace(' ','')
            }
            port_list.append(port_dict)
            csv_dict = {
                'switch': row['Switch'],
                'ports': port_list
            }
            csv_list.append(csv_dict)
    
    return csv_list

def main():
    '''Main function used to call all sub functions and passed looped data through each function'''
    #Get the orgs
    orgs = get_orgs()
    organizationId = None
    for org in orgs:
        if org['name'] == org_name:
            organizationId = org['id']
            break
    
    if not organizationId:
        print(f"Organization '{org_name}' not found!")
        return
    
    networks = get_networks(organizationId)
    networkId = None
    for network in networks:
        if network['name'] == net_name:
            networkId = network['id']
            break
    
    if not networkId:
        print(f"Network '{net_name}' not found!")
        return
        
    devices = get_devices(networkId)
    switches = open_csv()
    
    #Add metadata to the devices
    for switch in switches:
        switch_serial = None
        for device in devices:
            if switch['switch'] == device['name']:
                switch_serial = device['serial']
                switch['serial'] = switch_serial
                print(f"Found switch: {device['name']} ({switch_serial})")
                break
        
        if not switch_serial:
            print(f"Warning: Switch '{switch['switch']}' not found in network!")
            continue
        
        for port in switch['ports']:
            print(f"Updating port {port['port']} on {switch['switch']}")
            update_device(switch_serial, port)

if __name__ == '__main__':
    main()
