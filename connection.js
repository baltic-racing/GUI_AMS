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

async function load_ports() {
    try {
        const response = await fetch('/ports');
        const data = await response.json();
        const list = document.createElement('datalist');
        list.id = 'available_ports';
        for (const port of data.ports) {
            const option = document.createElement('option');
            option.value = port.port;
            option.label = port.description;
            list.appendChild(option);
        }
        document.body.appendChild(list);
        serial_port.setAttribute('list', list.id);
    } catch (error) {
        console.debug('Portliste nicht verfügbar', error);
    }
}
load_ports();
get_connection_state();
setInterval(get_connection_state, 1000);
