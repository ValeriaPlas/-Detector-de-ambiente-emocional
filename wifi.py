# wifi.py
import network
import time

def conectar(ssid, password, timeout=15):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(ssid, password)
        t0 = time.time()
        while not wlan.isconnected():
            if time.time() - t0 > timeout:
                raise OSError("Timeout conectando a WiFi")
            time.sleep(0.5)
    return wlan.ifconfig()
