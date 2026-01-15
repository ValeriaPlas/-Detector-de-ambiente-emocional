# prueba_spi.py
from machine import SPI, Pin
import time

SCK = 18
MOSI = 23
MISO = 19
CS = 5   # prueba también con otro pin si falla
BUS = 2

spi = SPI(BUS, baudrate=1000000, polarity=0, phase=1, sck=Pin(SCK), mosi=Pin(MOSI), miso=Pin(MISO))
cs = Pin(CS, Pin.OUT)
cs.value(1)

time.sleep_ms(50)

# Prueba 1: lectura simple
buf = bytearray(8)
cs.value(0)
# enviar 8 ceros y leer lo que responde la Pixy
spi.write_readinto(bytearray(8), buf)
cs.value(1)

print("Respuesta raw:", buf)

# Interpreta: si todo es 0x00 o 0xFF constantes probablemente NO hay enlace SPI correcto.
# Si hay bytes variados, la Pixy está respondiendo en el bus SPI.
