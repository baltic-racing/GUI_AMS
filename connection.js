// The server detects the USB port and baudrate independently of the page.
let connectionPollPending = false;
async function get_connection_state() {
    if (connectionPollPending) return;
    connectionPollPending = true;
    const status = document.querySelector('.usb-status');
    const dot = status.querySelector('circle');
    const label = document.getElementById('connection_status');
    const port = document.getElementById('connected_port');
    try {
        const response = await fetch('/connection', {cache: 'no-store', signal: AbortSignal.timeout(4000)});
        if (!response.ok) throw new Error('Verbindungsstatus nicht verfügbar');
        const data = await response.json();
        status.dataset.state = data.connected ? 'connected' : data.searching ? 'searching' : 'disconnected';
        dot.setAttribute('fill', data.connected ? '#208638' : data.searching ? '#e88a08' : '#d32f2f');
        label.textContent = data.connected ? 'USB verbunden'
            : data.searching ? 'USB nicht gefunden – wird gesucht' : 'USB getrennt';
        status.title = data.error || '';
        port.textContent = data.connected_port || '--';
    } catch (error) {
        status.dataset.state = 'disconnected';
        dot.setAttribute('fill', '#d32f2f');
        label.textContent = 'USB getrennt';
        status.title = 'GUI-Server nicht erreichbar';
        port.textContent = '--';
    } finally {
        connectionPollPending = false;
    }
}
get_connection_state();
window.addEventListener('focus', get_connection_state);
setInterval(get_connection_state, 1000);
