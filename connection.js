// Shared connection controls, preserving the existing page layout.
async function establish_connection() {
    try {
        const response = await fetch('/connection', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({port: serial_port.value, baudrate: Number(baud_rate.value)})
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Verbindung fehlgeschlagen');
        await get_connection_state();
    } catch (error) {
        document.getElementById('connection_status').textContent = error.message;
    }
}

async function disconnect() {
    try {
        await fetch('/connection', {method: 'DELETE'});
        await get_connection_state();
    } catch (error) {
        document.getElementById('connection_status').textContent = error.message;
    }
}

async function get_connection_state() {
    try {
        const response = await fetch('/connection');
        const data = await response.json();
        connect_button.style.display = data.connected ? 'none' : 'block';
        disconnect_button.style.display = data.connected ? 'block' : 'none';
        if (data.connected) serial_port.value = data.connected_port;
        const portLabel = document.getElementById('connected_port');
        if (portLabel) portLabel.textContent = data.connected_port || '--';
        document.getElementById('connection_status').textContent = data.connected
            ? `${data.connected_port}: ${data.receiving ? 'Messdaten werden empfangen' : 'Warte auf gültige Messdaten'}`
            : (data.error || 'Nicht verbunden');
        return data;
    } catch (error) {
        document.getElementById('connection_status').textContent = 'GUI-Server nicht erreichbar';
    }
}

const portList = document.createElement('datalist');
portList.id = 'available_ports';
document.body.appendChild(portList);
serial_port.setAttribute('list', portList.id);
const portHint = document.createElement('span');
portHint.id = 'port_status';
portHint.setAttribute('role', 'status');
document.getElementById('connection_status').after(portHint);
let portsLoading = false;
let portsSignature = null;

async function load_ports() {
    if (portsLoading) return;
    portsLoading = true;
    try {
        const response = await fetch('/ports', {cache: 'no-store'});
        if (!response.ok) throw new Error('Portliste konnte nicht geladen werden');
        const data = await response.json();
        const signature = JSON.stringify(data.ports);
        if (signature !== portsSignature) {
            portList.replaceChildren();
            for (const port of data.ports) {
                const option = document.createElement('option');
                option.value = port.port;
                option.label = port.description;
                portList.appendChild(option);
            }
            portsSignature = signature;
        }
        if (!serial_port.value.trim() && document.activeElement !== serial_port && data.ports.length === 1) {
            serial_port.value = data.ports[0].port;
        }
        portHint.textContent = data.ports.length
            ? ` Verfügbare Ports: ${data.ports.map(port => port.port).join(', ')}`
            : ' Windows meldet keinen COM-Port. Warte auf USB-Gerät …';
    } catch (error) {
        portHint.textContent = ' Portliste nicht verfügbar – GUI-Server prüfen.';
    } finally {
        portsLoading = false;
    }
}
serial_port.addEventListener('focus', load_ports);
window.addEventListener('focus', load_ports);
load_ports();
get_connection_state();
setInterval(load_ports, 2000);
setInterval(get_connection_state, 1000);
