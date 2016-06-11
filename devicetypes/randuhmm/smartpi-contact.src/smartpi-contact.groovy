/**
 *  Hub
 *
 *  Copyright 2016 Jonny Morrill
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 *  in compliance with the License. You may obtain a copy of the License at:
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 *  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License
 *  for the specific language governing permissions and limitations under the License.
 *
 */
metadata {
    definition (name: "SmartPi Contact", namespace: "randuhmm", author: "Jonny Morrill") {
        capability "Contact Sensor"
    }

    simulator {
        // TODO: define status and reply messages here
    }

    tiles {
        standardTile("button", "device.switch", width: 1, height: 1, canChangeIcon: true) {
            state "off", label: 'Off', icon: "st.Electronics.electronics18", backgroundColor: "#ffffff", nextState: "on"
            state "on", label: 'On', icon: "st.Electronics.electronics18", backgroundColor: "#79b821", nextState: "off"
        }
        main "button"
        details(["button"])
    }
}

// parse events into attributes
def parse(String description) {
    log.debug "Parsing '${description}'"
    // TODO: handle 'contact' attribute
    // TODO: handle 'switch' attribute
    // TODO: handle 'temperature' attribute
}

// handle commands
def on() {
    log.debug "Executing 'on'"
    // TODO: handle 'on' command
}

def off() {
    log.debug "Executing 'off'"
    // TODO: handle 'off' command
}

def sync(ip, port) {
    def existingIp = getDataValue("ip")
    def existingPort = getDataValue("port")
    if (ip && ip != existingIp) {
        updateDataValue("ip", ip)
    }
    if (port && port != existingPort) {
        updateDataValue("port", port)
    }
}

def restart() {
    subscribeAction("/path/of/event")
}

private subscribeAction(path, callbackPath="") {
    log.trace "subscribe($path, $callbackPath)"
    def address = getCallBackAddress()
    def ip = getHostAddress()

    def result = new physicalgraph.device.HubAction(
        method: "SUBSCRIBE",
        path: path,
        headers: [
            HOST: ip,
            CALLBACK: "<http://${address}/notify$callbackPath>",
            NT: "upnp:event",
            TIMEOUT: "Second-28800"
        ]
    )
    log.trace "SUBSCRIBE $path"
    return result
}

// gets the address of the hub
private getCallBackAddress() {
    return device.hub.getDataValue("localIP") + ":" + device.hub.getDataValue("localSrvPortTCP")
}

// gets the address of the device
private getHostAddress() {
    def ip = getDataValue("ip")
    def port = getDataValue("port")

    if (!ip || !port) {
        def parts = device.deviceNetworkId.split(":")
        if (parts.length == 2) {
            ip = parts[0]
            port = parts[1]
        } else {
            log.warn "Can't figure out ip and port for device: ${device.id}"
        }
    }

    log.debug "Using IP: $ip and port: $port for device: ${device.id}"
    return convertHexToIP(ip) + ":" + convertHexToInt(port)
}

private Integer convertHexToInt(hex) {
    return Integer.parseInt(hex,16)
}

private String convertHexToIP(hex) {
    return [convertHexToInt(hex[0..1]),convertHexToInt(hex[2..3]),convertHexToInt(hex[4..5]),convertHexToInt(hex[6..7])].join(".")
}