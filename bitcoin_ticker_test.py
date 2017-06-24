# WeMos D1 Mini -- Nokia 5110 PCD8544 LCD
# D3 (GPIO0) ----- 0 RST
# D4 (GPIO2) ----- 1 CE
# D8 (GPIO15) ---- 2 DC
# D7 (GPIO13) ---- 3 Din
# D5 (GPIO14) ---- 4 Clk
# 3V3 ------------ 5 Vcc
# D6 (GPIO12) ---- 6 BL
# G -------------- 7 Gnd

from machine import Pin, SPI
from pcd8544 import PCD8544
import time

spi = SPI(1)
spi.init(baudrate=8000000, polarity=0, phase=0)
cs = Pin(2, Pin.OUT)
dc = Pin(15, Pin.OUT)
rst = Pin(0, Pin.OUT)
bl = Pin(12, Pin.OUT, value=1)
lcd = PCD8544(spi, cs, dc, rst)

from bitcoin_ticker import BitcoinTicker

ticker = BitcoinTicker(lcd)

# new price displayed every 84 seconds
# the bottom 2 rows of pixels is a progress bar, incremented once per second
ticker.refresh()

# get new price immediately
# ticker.update()

# you can draw your own value using:
# ticker.draw("9999")
# ticker.draw("123")
# ticker.draw("44")
# ticker.draw("2")
