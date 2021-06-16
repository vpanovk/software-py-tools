import sys

import requests
import xlwt

from geojson_utils import centroid

topology = {}
portal_lights = []

APPS_URL = 'https://apps.cloud.us.kontakt.io'
IM_URL = 'https://api.kontakt.io'
ACCEPT_HEADER = 'application/vnd.com.kontakt+json;version=10'


def exit_with_usage():
    print("prepare_xls.py api_key campus_id")
    sys.exit(-1)


def fetch_portal_lights():
    pl = {}
    start_index = 0
    while True:
        response_json = requests.get(f'{IM_URL}/device',
                                     params={'startIndex': start_index, 'maxResult': 500, 'q': 'model==PORTAL_LIGHT'},
                                     headers={'Accept': ACCEPT_HEADER, 'Api-Key': api_key}).json()
        for device in response_json['devices']:
            mac = device['properties']['mac'].lower()
            mac_segments = mac.split(':')
            last_segment_no = int(mac_segments[-1], 16)
            last_segment_ble = (last_segment_no + 2) % 256
            mac_segments[-1] = "{0:02x}".format(last_segment_ble)
            pl[device['uniqueId']] = ":".join(mac_segments)

        start_index += 500
        if len(response_json['searchMeta']['nextResults']) == 0:
            break
    return pl


def fetch_portal_beams():
    beams = {}
    start_index = 0
    while True:
        response_json = requests.get(f'{IM_URL}/device',
                                     params={'startIndex': start_index, 'maxResult': 500, 'q': 'model==PORTAL_BEAM'},
                                     headers={'Accept': ACCEPT_HEADER, 'Api-Key': api_key}).json()
        for device in response_json['devices']:
            mac = device['mac'].lower()
            beams[mac] = device['uniqueId']

        start_index += 500
        if len(response_json['searchMeta']['nextResults']) == 0:
            break
    return beams


def fetch_beacons():
    beacons = {}
    start_index = 0
    while True:
        response_json = requests.get(f'{IM_URL}/device',
                                     params={'startIndex': start_index, 'maxResult': 500, 'q': '(model!=PORTAL_BEAM&model!=PORTAL_LIGHT)', 'selector': 'mac'},
                                     headers={'Accept': ACCEPT_HEADER, 'Api-Key': api_key}).json()
        for device in response_json['devices']:
            mac = device['mac'].lower()
            beacons[mac] = device['uniqueId']

        start_index += 500
        if len(response_json['searchMeta']['nextResults']) == 0:
            break
    return beacons


def write_array_to_sheet(sheet, row, array):
    for i in range(0, len(array)):
        sheet.write(row, i, array[i])


def emit_portal_lights(topology, portal_light_macs):
    pl_info_workbook = xlwt.Workbook()
    pl_info_sheet = pl_info_workbook.add_sheet("Sheet 1")
    num = 1
    write_array_to_sheet(pl_info_sheet, 0, ['num', 'building_id', 'floor_id', 'x', 'y', 'z', 'id', 'mac'])
    for building in topology['buildings']:
        for floor in building['floors']:
            for gateway in floor['gateways']:
                write_array_to_sheet(pl_info_sheet, num, [
                    num,
                    building['id'],
                    floor['id'],
                    gateway['x'],
                    gateway['y'],
                    0,
                    gateway['sourceId'],
                    portal_light_macs[gateway['sourceId']]
                ])
                num = num + 1
    pl_info_workbook.save('pl_info.xls')

def emit_installation_info(topology):
    installation_info_workbook = xlwt.Workbook()
    installation_info_sheet = installation_info_workbook.add_sheet("Sheet 1")
    write_array_to_sheet(installation_info_sheet, 0, [
        'type', 'building', 'floor', 'grid_id', 'center_x', 'center_y', 'ir_id', 'point_num'])

    num = 1

    for building in topology['buildings']:
        for floor in building['floors']:
            array = [
                1,
                building['id'],
                floor['id'],
                -1,  # grid_id
                -1,  # center_x
                -1,  # center_y
                -1,  # ir_id,
                len(floor['xyGeojson']['geometry']['coordinates'][0])
            ]
            array.extend([c[0] for c in floor['xyGeojson']['geometry']['coordinates'][0]])
            array.extend([c[1] for c in floor['xyGeojson']['geometry']['coordinates'][0]])
            write_array_to_sheet(installation_info_sheet, num, array)
            num = num + 1
            for room in floor['rooms']:
                center = centroid(room['xyGeojson']['geometry'])
                center_coords = center['coordinates']
                array = [
                    1,
                    building['id'],
                    floor['id'],
                    room['id'],
                    center_coords[0],
                    center_coords[1],
                    room['roomNumber'],
                    len(room['xyGeojson']['geometry']['coordinates'][0])
                ]
                array.extend([c[0] for c in room['xyGeojson']['geometry']['coordinates'][0]])
                array.extend([c[1] for c in room['xyGeojson']['geometry']['coordinates'][0]])
                write_array_to_sheet(installation_info_sheet, num, array)
                num = num + 1

    installation_info_workbook.save('installation_info.xls')


def emit_beam_info(topology, beams):
    beam_info_workbook = xlwt.Workbook()
    beam_info_sheet = beam_info_workbook.add_sheet("Sheet 1")
    write_array_to_sheet(beam_info_sheet, 0, ['num', 'building_id', 'floor_id', 'x', 'y', 'z', 'grid_id', 'mac', 'id'])

    num = 1

    for building in topology['buildings']:
        for floor in building['floors']:
            for room in floor['rooms']:
                for room_sensor in room['roomSensors']:
                    write_array_to_sheet(beam_info_sheet, num, [
                        num,
                        building['id'],
                        floor['id'],
                        room_sensor['x'],
                        room_sensor['y'],
                        0,
                        room['id'],
                        room_sensor['trackingId'],
                        beams[room_sensor['trackingId']]
                    ])
                    num = num + 1
    beam_info_workbook.save('beam_info.xls')


def emit_ir_info(topology, beams):
    ir_info_workbook = xlwt.Workbook()
    ir_info_sheet = ir_info_workbook.add_sheet("Sheet 1")
    write_array_to_sheet(ir_info_sheet, 0, ['num', 'building_id', 'floor_id', 'x', 'y', 'z', 'ir_id', 'room_id', 'mac', 'id'])

    num = 1

    for building in topology['buildings']:
        for floor in building['floors']:
            for room in floor['rooms']:
                for room_sensor in room['roomSensors']:
                    write_array_to_sheet(ir_info_sheet, num, [
                        num,
                        building['id'],
                        floor['id'],
                        room_sensor['x'],
                        room_sensor['y'],
                        0,
                        room['roomNumber'],
                        room['id'],
                        room_sensor['trackingId'],
                        beams[room_sensor['trackingId']]
                    ])
                    num = num + 1
    ir_info_workbook.save('ir_info.xls')


def emit_beacon_list(beacons):
    beacon_list_workbook = xlwt.Workbook()
    beacon_list_sheet = beacon_list_workbook.add_sheet("Sheet 1")
    write_array_to_sheet(beacon_list_sheet, 0, ['id', 'mac', 'beacon_type'])
    num = 1
    for mac, unique_id in beacons.items():
        write_array_to_sheet(beacon_list_sheet, num, [
            unique_id,
            mac,
            0
        ])
        num = num + 1
    beacon_list_workbook.save('beacon_list.xls')


if len(sys.argv) != 3:
    exit_with_usage()
api_key = sys.argv[1]
campus_id = sys.argv[2]

topology = requests.get(f'{APPS_URL}/v2/locations/campuses/{campus_id}',
                        headers={'Api-Key': api_key}).json()
portal_lights = fetch_portal_lights()
beams = fetch_portal_beams()
beacons = fetch_beacons()

emit_portal_lights(topology, portal_lights)
emit_installation_info(topology)
emit_beam_info(topology, beams)
emit_ir_info(topology, beams)
emit_beacon_list(beacons)
