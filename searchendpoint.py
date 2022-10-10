#!/usr/bin/python3

import requests
import json
import signal
import sys

signal.signal(signal.SIGPIPE, signal.SIG_DFL) # IOError: Broken pipe
signal.signal(signal.SIGINT, signal.SIG_DFL) #Keyboardinterrupt: Ctrl-C


token = "INSERT-TOKEN"
headers = {'Authorization': "Bearer {}".format(token)}

def mac_vendors_api(macadd):
    return(f'''http://api.macvendors.com/{macadd}''')

def librenms_arp(macadd):
    return(f'''https://librenms.domain.com/api/v0/resources/ip/arp/{macadd}''')

def librenms_svi(device_id):
    return(f'''https://librenms.domain.com/api/v0/devices/{device_id}/ip''')

def librenms_fdb(macadd):
    return(f'''https://librenms.domain.com/api/v0/resources/fdb/{macadd}''')

def librenms_connected_device(connected_device):
    return (f'''https://librenms.domain.com/api/v0/devices/{connected_device}''')

def librenms_port_id(portid):
    return (f'''https://librenms.domain.com/api/v0/ports/{portid}''')

def librenms_port_mac(macadd):
    return (f'''https://librenms.domain.com/api/v0/ports/mac/{macadd}''')

def librenms_get_vlans():
    return (f'''https://librenms.domain.com/api/v0/resources/vlans/''')

def librenms_device_fdb(device_id):
    return (f'''https://librenms.domain.com/api/v0/devices/{device_id}/fdb''')


def main():
    print (f'''--------------------------------------------------------------------------------------------------------
Script check librenms.domain.com to see if device is attached to  network and looks up manufacturer through macvendors.com.
LibreNMS information may not be up to date due to polling intervalls.
--------------------------------------------------------------------------------------------------------''')
    # Input
    try:
        input_address = sys.argv[1]
    except:
        input_address = input('Enter MAC or IP-address: ')
        print('--------------------------------------------------------------------------------------------------------')

        
    # Search for MAC/IP in LibreNMS arp-table, exits program if not found 
    search_librenms_arp = librenms_arp(input_address)
    api_search_librenms_arp = requests.get(search_librenms_arp, headers=headers)
    if api_search_librenms_arp.json()['count'] == 0:
        search_mac = mac_vendors_api(input_address)
        api_search_mac = requests.get(search_mac)
        if 'Not Found' in api_search_mac.text:
            print('Unknown MAC-address or IP-address was not found in ARP-table.')
        else:
            print('NIC manufacturer:', api_search_mac.text)
        search_librenms_connected_device = librenms_port_mac(input_address)
        api_search_librenms_connected_device = requests.get(search_librenms_connected_device, headers=headers)
        print_api_search_librenms_connected_device = json.loads(api_search_librenms_connected_device.text)
        if 'mac not found' in api_search_librenms_connected_device.text:
            print('Not found in LibreNMS, terminating script.')
            sys.exit()
        connected_interface = None
        for port_mac_result in print_api_search_librenms_connected_device['ports']:
            if port_mac_result['ifTrunk'] != "dot1Q":
                connected_interface = port_mac_result['ifDescr']
                connected_interface_description = port_mac_result['ifAlias']
                connected_interface_id = port_mac_result['port_id']
                connected_device_id = port_mac_result['device_id']
            if connected_interface == None and port_mac_result['device_id']:
                connected_interface = port_mac_result['ifDescr']
                connected_interface_description = port_mac_result['ifAlias']
                connected_interface_id = port_mac_result['port_id']
                connected_device_id = port_mac_result['device_id']
        search_librenms_physical_device = librenms_connected_device(connected_device_id)
        api_search_librenms_physical_device = requests.get(search_librenms_physical_device, headers=headers)
        connected_device = api_search_librenms_physical_device.json()['devices'][0]['hostname']
        search_fdb_connected_device = librenms_device_fdb(connected_device_id)
        api_search_fdb_connected_device = requests.get(search_fdb_connected_device, headers=headers)
        api_search_fdb_connected_device_result = json.loads(api_search_fdb_connected_device.text)
        for port_result in api_search_fdb_connected_device_result['ports_fdb']:
            if port_result['port_id'] == connected_interface_id:
                true_vlan = port_result['vlan_id']
        if true_vlan != 0:
            get_librenms_vlans = librenms_get_vlans()
            api_get_librenms_vlans = requests.get(get_librenms_vlans, headers=headers)
            api_get_librenms_vlans_result = json.loads(api_get_librenms_vlans.text)
            for vlan_result in api_get_librenms_vlans_result['vlans']:
                if vlan_result['vlan_id'] == int(true_vlan):
                    vlan_id = vlan_result['vlan_vlan']
                    vlan_name = vlan_result['vlan_name']


        print(f'''--------------------------------------------------------------------------------------------------------
Only L2 information is availible.
Device is connected to: {connected_device}
Interface: {connected_interface}
Interface description: {connected_interface_description}
Interface VLAN: {vlan_id}
VLAN name: {vlan_name}
--------------------------------------------------------------------------------------------------------''')
        sys.exit()
    api_search_librenms_arp_ip = api_search_librenms_arp.json()['arp'][0]['ipv4_address']
    api_search_librenms_arp_mac = api_search_librenms_arp.json()['arp'][0]['mac_address']
    api_search_librenms_arp_device = api_search_librenms_arp.json()['arp'][0]['device_id']
    api_search_librenms_arp_port_id = api_search_librenms_arp.json()['arp'][0]['port_id']
    search_librenms_svi_device = librenms_connected_device(api_search_librenms_arp_device)
    api_search_librenms_svi_device = requests.get(search_librenms_svi_device, headers=headers)
    svi_device = api_search_librenms_svi_device.json()['devices'][0]['hostname']

    # Check LibreNMS for which IP-network it belongs too
    search_librenms_connected_svi = librenms_svi(api_search_librenms_arp_device)
    api_search_librenms_connected_svi = requests.get(search_librenms_connected_svi, headers=headers)
    api_search_librenms_connected_svi_result = json.loads(api_search_librenms_connected_svi.text)
    for svi_results in api_search_librenms_connected_svi_result['addresses']:
        if svi_results['port_id'] == api_search_librenms_arp_port_id and 'ipv4_address' in svi_results:
            svi_address = svi_results['ipv4_address']
            svi_netmask = svi_results['ipv4_prefixlen']
    if svi_address == api_search_librenms_arp_ip:
        print(f'''
Device IP-address: {api_search_librenms_arp_ip} 
Device MAC-address: {api_search_librenms_arp_mac} 
SVI configured in: {svi_device}
SVI IP-address is: {svi_address}/{svi_netmask}

The IP address searched for is the IP address of an SVI.
--------------------------------------------------------------------------------------------------------''')  
        sys.exit()


    # Checks MAC-address towards macvendors.com 
    search_mac = mac_vendors_api(api_search_librenms_arp_mac)
    api_search_mac = requests.get(search_mac)
    if 'Not Found' in api_search_mac.text:
        print('Unknown MAC-address.')
    else:
        print('NIC manufacturer:', api_search_mac.text)

    # Find information regarding which device MAC/IP is connected to
    search_librenms_connected_device = librenms_port_mac(api_search_librenms_arp_mac)
    api_search_librenms_connected_device = requests.get(search_librenms_connected_device, headers=headers)
    print_api_search_librenms_connected_device = json.loads(api_search_librenms_connected_device.text)
    connected_interface = None
    for port_mac_result in print_api_search_librenms_connected_device['ports']:
        if port_mac_result['ifTrunk'] != "dot1Q":
            connected_interface = port_mac_result['ifDescr']
            connected_interface_description = port_mac_result['ifAlias']
            connected_interface_id = port_mac_result['port_id']
            connected_device_id = port_mac_result['device_id']
        if connected_interface == None and port_mac_result['device_id']:
            connected_interface = port_mac_result['ifDescr']
            connected_interface_description = port_mac_result['ifAlias']
            connected_interface_id = port_mac_result['port_id']
            connected_device_id = port_mac_result['device_id']    
    search_librenms_physical_device = librenms_connected_device(connected_device_id)
    api_search_librenms_physical_device = requests.get(search_librenms_physical_device, headers=headers)
    connected_device = api_search_librenms_physical_device.json()['devices'][0]['hostname']
    search_fdb_connected_device = librenms_device_fdb(connected_device_id)
    api_search_fdb_connected_device = requests.get(search_fdb_connected_device, headers=headers)
    api_search_fdb_connected_device_result = json.loads(api_search_fdb_connected_device.text)
    for port_result in api_search_fdb_connected_device_result['ports_fdb']:
        if port_result['port_id'] == connected_interface_id:
            true_vlan = port_result['vlan_id']
    if true_vlan != 0:
        get_librenms_vlans = librenms_get_vlans()
        api_get_librenms_vlans = requests.get(get_librenms_vlans, headers=headers)
        api_get_librenms_vlans_result = json.loads(api_get_librenms_vlans.text)
        for vlan_result in api_get_librenms_vlans_result['vlans']:
            if vlan_result['vlan_id'] == int(true_vlan):
                vlan_id = vlan_result['vlan_vlan']
                vlan_name = vlan_result['vlan_name']
    else:
            print(f'''--------------------------------------------------------------------------------------------------------
Device IP-address: {api_search_librenms_arp_ip} 
Device MAC-address: {api_search_librenms_arp_mac} 
SVI configured in: {svi_device}
SVI IP-address is: {svi_address}/{svi_netmask}
Device is connected to: {connected_device}
Interface: {connected_interface}
Interface description: {connected_interface_description}
VLAN information is not availible.
--------------------------------------------------------------------------------------------------------''')
            sys.exit()



        
# Print what has been found in LibreNMS
    print(f'''--------------------------------------------------------------------------------------------------------
Device IP-address: {api_search_librenms_arp_ip} 
Device MAC-address: {api_search_librenms_arp_mac} 
SVI configured in: {svi_device}
SVI IP-address is: {svi_address}/{svi_netmask}
Device is connected to: {connected_device}
Interface: {connected_interface}
Interface description: {connected_interface_description}
Interface VLAN: {vlan_id}
VLAN name: {vlan_name}
--------------------------------------------------------------------------------------------------------''')
if __name__ == '__main__':
    main()
