# Copyright 2015, Markus Birth
# markus@birth-online.de
# https://github.com/mbirth/wipy-upcd8544/commit/3ec86e22282e59eacc98fdf303c58166c3e138c7

# with modifications by Mike Causer for ESP8266
# https://github.com/mbirth/wipy-upcd8544/issues/1
import machine
import ustruct as struct
import time

class PCD8544:
	ADDRESSING_HORIZ = 0x00
	ADDRESSING_VERT = 0x02
	INSTR_BASIC = 0x00
	INSTR_EXT = 0x01
	POWER_UP = 0x00
	POWER_DOWN = 0x04
	DISPLAY_BLANK = 0x08
	DISPLAY_ALL = 0x09
	DISPLAY_NORMAL = 0x0c
	DISPLAY_INVERSE = 0x0d
	TEMP_COEFF_0 = 0x04
	TEMP_COEFF_1 = 0x05
	TEMP_COEFF_2 = 0x06
	TEMP_COEFF_3 = 0x07
	BIAS_1_4 = 0x17
	BIAS_1_5 = 0x16
	BIAS_1_6 = 0x15
	BIAS_1_7 = 0x14
	BIAS_1_8 = 0x13
	BIAS_1_9 = 0x12
	BIAS_1_10 = 0x11
	BIAS_1_11 = 0x10

	def __init__(self, spi, rst, ce, dc, light, pwr=None):
		self.width = 84
		self.height = 48
		self.power = self.POWER_DOWN
		self.addressing = self.ADDRESSING_HORIZ
		self.instr = self.INSTR_BASIC
		self.display_mode = self.DISPLAY_BLANK
		self.temp_coeff = self.TEMP_COEFF_0
		self.bias = self.BIAS_1_11
		self.voltage = 3060

		if "OUT_PP" in dir(rst):
			rst.init(rst.OUT_PP, rst.PULL_NONE)
			ce.init(ce.OUT_PP, ce.PULL_NONE)
			dc.init(dc.OUT_PP, dc.PULL_NONE)
			light.init(light.OUT_PP, light.PULL_NONE)
			if pwr:
				pwr.init(pwr.OUT_PP, pwr.PULL_NONE)
		else:
			# WiPy style
			rst.init(rst.OUT, None)
			ce.init(ce.OUT, None)
			dc.init(dc.OUT, None)
			light.init(light.OUT, None)
			if pwr:
				pwr.init(pwr.OUT, None)

		self.spi = spi
		self.rst = rst
		self.ce = ce
		self.dc = dc
		self.light = light
		self.pwr = pwr

		self.light_off()
		self.power_on()
		self.ce.value(1)
		self.reset()
		self.set_contrast(0xbf)
		self.clear()

	def _set_function(self):
		value = 0x20 | self.power | self.addressing | self.instr
		self.command([value])

	def set_power(self, power, set=True):
		assert power in [self.POWER_UP, self.POWER_DOWN], "Power must be POWER_UP or POWER_DOWN."
		self.power = power
		if set:
			self._set_function()

	def set_adressing(self, addr, set=True):
		assert addr in [self.ADDRESSING_HORIZ, self.ADDRESSING_VERT], "Addressing must be ADDRESSING_HORIZ or ADDRESSING_VERT."
		self.addressing = addr
		if set:
			self._set_function()

	def set_instr(self, instr, set=True):
		assert instr in [self.INSTR_BASIC, self.INSTR_EXT], "Instr must be INSTR_BASIC or INSTR_EXT."
		self.instr = instr
		if set:
			self._set_function()

	def set_display(self, display_mode):
		assert display_mode in [self.DISPLAY_BLANK, self.DISPLAY_ALL, self.DISPLAY_NORMAL, self.DISPLAY_INVERSE], "Mode must be one of DISPLAY_BLANK, DISPLAY_ALL, DISPLAY_NORMAL or DISPLAY_INVERSE."
		assert self.instr == self.INSTR_BASIC, "Please switch to basic instruction set first."
		self.display_mode = display_mode
		self.command([display_mode])

	def set_temp_coeff(self, temp_coeff):
		assert 4 <= temp_coeff < 8, "Temperature coefficient must be one of TEMP_COEFF_0..TEMP_COEFF_3."
		assert self.instr == self.INSTR_EXT, "Please switch to extended instruction set first."
		self.temp_coeff = temp_coeff
		self.command([temp_coeff])

	def set_bias(self, bias):
		assert 0x10 <= bias <= 0x17, "Bias must be one of BIAS_1_4..BIAS_1_11."
		assert self.instr == self.INSTR_EXT, "Please switch to extended instruction set first."
		self.bias = bias
		self.command([bias])

	def set_voltage(self, millivolts):
		assert 3060 <= millivolts <= 10680, "Voltage must be between 3,060 and 10,680 mV."
		assert self.instr == self.INSTR_EXT, "Please switch to extended instruction set first."
		self.voltage = millivolts
		basevoltage = millivolts - 3060
		incrementor = basevoltage // 60
		code = 0x80 & incrementor
		self.command([code])

	def set_contrast(self, value):
		assert 0x80 <= value <= 0xff, "contrast value must be between 0x80 and 0xff"
		self.command([0x21, self.TEMP_COEFF_2, self.BIAS_1_7, value, 0x20, self.DISPLAY_NORMAL])

	def position(self, x, y):
		assert 0 <= x < self.width, "x must be between 0 and 83"
		assert 0 <= y < self.height // 8, "y must be between 0 and 5"
		assert self.instr == self.INSTR_BASIC, "Please switch to basic instruction set first."
		self.command([x + 0x80, y + 0x40])

	def clear(self):
		self.position(0, 0)
		self.data([0] * (self.height * self.width // 8))
		self.position(0, 0)

	def sleep_ms(self, mseconds):
		time.sleep_ms(mseconds)

	def sleep_us(self, useconds):
		time.sleep_us(useconds)

	def power_on(self):
		if self.pwr:
			self.pwr.value(1)
		self.reset()

	def reset(self):
		self.rst.value(0)
		self.sleep_us(100)
		self.rst.value(1)
		self.power = self.POWER_DOWN
		self.addressing = self.ADDRESSING_HORIZ
		self.instr = self.INSTR_BASIC
		self.display_mode = self.DISPLAY_BLANK
		self.temp_coeff = self.TEMP_COEFF_0
		self.bias = self.BIAS_1_11
		self.voltage = 3060

	def power_off(self):
		self.clear()
		self.command([0x20, 0x08])
		self.sleep_ms(10)
		if self.pwr:
			self.pwr.value(0)

	def command(self, arr):
		self.bitmap(arr, 0)

	def data(self, arr):
		self.bitmap(arr, 1)

	def bitmap(self, arr, dc):
		self.dc.value(dc)
		buf = struct.pack('B'*len(arr), *arr)
		self.ce.value(0)
		self.spi.write(buf)
		self.ce.value(1)

	def light_on(self):
		self.light.value(0)

	def light_off(self):
		self.light.value(1)
