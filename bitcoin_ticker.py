"""MicroPython bitcoin price index ticker.

Usage:
	from machine import Pin, SPI
	from upcd8544 import PCD8544
	import time

	spi = SPI(1)
	spi.init(baudrate=8000000, polarity=0, phase=0)
	RST = Pin(0, Pin.OUT)
	CE = Pin(2, Pin.OUT)
	DC = Pin(15, Pin.OUT)
	BL = Pin(12, Pin.OUT)
	lcd = PCD8544(spi, RST, CE, DC, BL)

	from bitcoin_ticker import BitcoinTicker
	ticker = BitcoinTicker(lcd)
	ticker.refresh()
"""

from micropython import const

from framebuf import FrameBuffer1
from time import sleep
import urequests

SPACE = const(2)	# between characters
YPOS = const(13)	# roughly (lcd height - font height - progress bar height) / 2

# bitcoin symbol (2px taller than the other chars)
btc = FrameBuffer1(bytearray(b'\x18\x18\xf8\xf8\xff\xff\x18\x1f\x1f8x\xf8\xf0\xe0\x00\x00\x00\xff\xff\xff\xff\x06\x06\x06\x06\x8f\xdf\xff\xfd\xf8\x03\x03\x03\x03\x1f\x1f\x03\x1f\x1f\x03\x03\x03\x03\x01\x00'), 15, 21)

# digits (0-9, variable width)
b0 = FrameBuffer1(bytearray(b'\xc0\xf0\xfc<\x0e\x07\x07\x07\x07\x0f\x1e>\xfc\xf0\xc0\x1f\x7f\xff\xe0\xc0\x80\x00\x00\x00\x00\x80\xe0\xff\x7f\x1f\x00\x00\x01\x03\x03\x07\x07\x07\x07\x07\x03\x01\x01\x00\x00'), 15, 19)
b1 = FrameBuffer1(bytearray(b'\x04\x0e\x0e\x0e\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\x00\x00\x00\x00\x07\x07\x07'), 7, 19)
b2 = FrameBuffer1(bytearray(b'\x00\x18<\x1e\x0e\x07\x07\x07\x07\x0f\xfe\xfc\xf8\x00\x80\x80\xc0\xe0\xf0x<\x1e\x0f\x07\x03\x00\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07'), 13, 19)
b3 = FrameBuffer1(bytearray(b'\x00\x07\x07\x07\x07\xc7\xe7\xf7\x7f?\x1f\x0f\x07\x80\xc0\xc0\x80\x03\x03\x03\x03\x07\x8f\xfe\xfe\xf8\x00\x01\x03\x03\x07\x07\x07\x07\x07\x03\x03\x01\x00'), 13, 19)
b4 = FrameBuffer1(bytearray(b'\x00\x00\x00\x00\x80\xc0\xe0\xf0|\x1e\xff\xff\xff\x00\x00\x00\x10x|\x7f\x7fsqppp\xff\xff\xffppp\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x07\x07\x07\x00\x00\x00'), 16, 19)
b5 = FrameBuffer1(bytearray(b'\x00\xff\xff\xff\x87\x87\x87\x87\x87\x07\x07\x07\x00\x80\xc3\x87\x83\x03\x03\x03\x03\x03\x87\xff\xfe|\x01\x03\x03\x07\x07\x07\x07\x07\x07\x03\x03\x01\x00'), 13, 19)
b6 = FrameBuffer1(bytearray(b'\xc0\xf0\xfc>\x0e\x87\x87\x87\x87\x0f\x1e\x06\x00?\xff\xff\x87\x03\x03\x03\x03\x03\x87\xff\xfex\x00\x00\x01\x03\x07\x07\x07\x07\x07\x03\x03\x01\x00'), 13, 19)
b7 = FrameBuffer1(bytearray(b'\x07\x07\x07\x07\x07\x07\x07\xc7\xf7\xff\x7f\x1f\x07\x00\x00\x00\xc0\xf0\xfc\x7f\x1f\x07\x01\x00\x00\x00\x00\x04\x07\x07\x07\x01\x00\x00\x00\x00\x00\x00\x00'), 13, 19)
b8 = FrameBuffer1(bytearray(b'\x00x\xfc\xfe\x8f\x07\x07\x07\x07\x8f\xfe\xfcx\x00\xf0\xf8\xfc\x8f\x0f\x07\x07\x07\x07\x0f\x8f\xfd\xf8\xf0\x00\x01\x03\x03\x07\x07\x07\x07\x07\x07\x03\x03\x01\x00'), 14, 19)
b9 = FrameBuffer1(bytearray(b'\xf0\xfc\xfe\x0e\x07\x07\x07\x07\x0f\x1e\xfc\xf8\xe0\x01\x87\x8f\x0f\x1e\x1c\x1c\x1c\x8e\xc7\xff\x7f\x1f\x01\x03\x03\x07\x07\x07\x07\x07\x03\x03\x01\x00\x00'), 13, 19)

# characters (0-9, btc symbol)
characters = [b0,b1,b2,b3,b4,b5,b6,b7,b8,b9,btc]

# character widths (0-9, btc symbol)
widths = [15,7,13,13,16,13,13,13,14,13,15]

class BitcoinTicker:
	def __init__(self, lcd):
		self.lcd = lcd

		self.width = self.lcd.width		# 84
		self.height = self.lcd.height	# 48

		# backlight
		self.lcd.light_on()
		# self.lcd.light_off()

		# the main FrameBuffer
		self.buffer = bytearray((self.height // 8) * self.width)
		self.framebuf = FrameBuffer1(self.buffer, self.width, self.height)

	def refresh(self):
		while(True):
			# display results
			self.update()
			sleep(1)

			# increment progress bar
			for i in range(1,85,1):
				self.framebuf.fill_rect(0,46,i,2,1)
				self.lcd.data(self.buffer)
				sleep(1)

	def update(self):
		# change this to the currency of your choice
		res = urequests.get("http://api.coindesk.com/v1/bpi/currentprice/AUD.json").json()
		# change this too
		self.draw('%d' % res['bpi']['AUD']['rate_float'])

	def draw(self, string):
		# clear
		self.framebuf.fill(0)
		self.lcd.data(self.buffer)

		# figure out bounding box
		xpos = widths[10] + SPACE
		for c in string:
			i = int(c)
			xpos += widths[i] + SPACE
		xpos = (self.width - xpos) // 2

		# draw symbol
		self.framebuf.blit(btc, xpos, YPOS - 1)
		xpos += widths[10] + SPACE

		# draw each digit
		for c in string:
			i = int(c)
			self.framebuf.blit(characters[i], xpos, YPOS)
			xpos += widths[i] + SPACE

		self.lcd.data(self.buffer)
