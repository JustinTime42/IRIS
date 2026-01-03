from machine import I2C, Pin
from micropython import const
from ustruct import unpack
import time

_REG_CHIP_ID     = const(0x00)
_REG_REV_ID      = const(0x01)
_REG_STATUS      = const(0x03)
_REG_MEASURE     = const(0x04)
_REG_TIME        = const(0x0C)
_REG_INT_STATUS  = const(0x11)
_REG_FIFO_LENGTH = const(0x12)
_REG_FIFO_DATA   = const(0x14)
_REG_FIFO_CMD    = const(0x17)
_REG_FIFO_CONFIG = const(0x18)
_REG_INT_CTRL    = const(0x19)
_REG_PWR_CTRL    = const(0x1B)
_REG_OSR         = const(0x1C)
_REG_ODR         = const(0x1D)
_REG_CONFIG      = const(0x1F)
_REG_CMD         = const(0x7E)
_REG_COEFF       = const(0x31)

_CMD_CTRL_SLEEP  = const(0x00)
_CMD_CTRL_FORCED = const(0x13)
_CMD_CTRL_NORMAL = const(0x33)
_CMD_RESET       = const(0xB6)
_CMD_FIFO_START  = const(0x1B)
_CMD_FIFO_STOP   = const(0x00)
_CMD_FIFO_FLUSH  = const(0xB0)

_FIFO_CONFIG        = const(0x08)
_FIFO_SENSOR_FRAME  = const(0x94)
_ADCT_FORCED        = const(50)  # 50ms - BMP388 needs ~34ms typical for forced measurement

# Over-sampling setting per mode.
OSR = (0x00, 0x0D)
# IIR filter coefficient per mode.
CONFIG = (0x00, 0x0A)

# Convert Celsius to Fahrenheit
CtoF = lambda C, d=1: round((C * 9/5) +32, d)

# Convert feet to meters
FtoM = lambda F: int(F / 3.28084)

class BMP3XX():
    def __init__(self, ADDR=0x76):
        self.ADDR = ADDR
        # Initialize I2C for Raspberry Pi Pico W per PINOUT (GP6 SDA, GP7 SCL)
        # Reason: micro:bit provides a global i2c; Pico W requires explicit init.
        global i2c
        try:
            i2c
        except NameError:
            # Use 100kHz instead of 400kHz for better reliability
            i2c = I2C(1, scl=Pin(7), sda=Pin(6), freq=100000)
        self._Load_Calibration_Data()
        self.SetMode()

    # Mode 0 : Forced readings, lower resolution
    # Mode 1 : Continuous readings, highest resolution
    # odr_set defines period of continuous sampling.
    # It has a value between 4 and 17 where
    # Period = 5 * (odr_set ** 2) in ms.
    def SetMode(self, Mode=0, odr_set=4):
        if Mode not in (0, 1):
            Mode = 0
        self.Mode = Mode
        self._Reset()
        time.sleep_ms(20)
        # Set IIR Filter Coefficient.
        self._writeReg([_REG_CONFIG, CONFIG[self.Mode]])
        # Set temperature & pressure over-sampling.
        self._writeReg([_REG_OSR, OSR[self.Mode]])
        if self.Mode == 1:
            if odr_set < 4:
                odr_set = 4
            elif odr_set > 17:
                odr_set = 17
            self.odr_set = odr_set
            # Start Normal sampling
            self._writeReg([_REG_ODR, odr_set])
            self._writeReg([_REG_PWR_CTRL, _CMD_CTRL_NORMAL])
            #sleep(int(5 * 2**odr_set + 1))
        else:
            self.odr_set = None

    # If Mode 1 (Normal) is active this method
    # will put the sensor to sleep.
    # All registers are still available but
    # no measurements are taken.
    def SleepOn(self):
        if self.Mode == 1:
            self._writeReg([_REG_PWR_CTRL, _CMD_CTRL_SLEEP])
            
    # Wakes the sensor up into Mode 1.
    # This Normal (continuous) sampling with the
    # settings that were in place before sleep.
    def SleepOff(self):
        if self.Mode == 1:
            self.SetMode(1)

# *******************************************
#              Properties
# *******************************************

    # Trigger and return both temperature
    # and pressure measurements.
    @property
    def Reading(self):
        # Read uncompensated temperature and pressure.
        if self.Mode == 0:
            self._writeReg([_REG_PWR_CTRL, _CMD_CTRL_FORCED])
            time.sleep_ms(_ADCT_FORCED)
        buf = self._readReg(_REG_MEASURE, 6)
        pressure = buf[0] + buf[1]*256 + buf[2]*65536
        temperature = buf[3] + buf[4]*256 + buf[5]*65536
        # Convert to actual values
        return self._Compensate(temperature, pressure)

    # Returns temperature only
    @property
    def T(self):
        return self.Reading[0]

    # Returns pressure only
    @property
    def P(self):
        return self.Reading[1]

    # Returns the chip's ID
    @property
    def ID(self):
        id = self._readReg(_REG_CHIP_ID, 1)
        return hex(id[0])

    # Chip revision number.
    # Overridden by child method where appropriate.
    @property
    def RevID(self):
        return None

    # Returns the sensor time.
    # Clock frequency appears to be ~26kHz.
    # Value returned is an unsigned 32-bit integer.
    # There is no information in the product
    # datasheet about its meaning.
    @property
    def Time(self):
        buf = self._readReg(_REG_TIME, 3)
        time = buf[2] * 65536 + buf[1] * 256 + buf[0]
        return time

    # Returns True if there is pressure and/or
    # temperature value(s) ready to be read.
    @property
    def IsDataReady(self):
        buf = self._readReg(_REG_STATUS, 1)
        return (buf[0] & 0b1100000) == 0b1100000

    # Returns Mode where:
    # 0 : Forced sampling mode.
    # 1 : Normal (continuous) sampling mode.
    @property
    def GetMode(self):
        return self.Mode

    # Returns odr_set parameter.
    # This value determines the sampling period
    # when the sensor is in Mode 1 i.e Normal
    # (continuous) sampling mode.
    # Period = 5 * (odr_set ** 2) in ms.
    @property
    def GetODR(self):
        return self.odr_set

# *******************************************
#          FIFO Methods and Properties
# *******************************************

    # Starts writing temperature and pressure
    # uncompensated values to the FIFO queue.
    def FIFOStart(self):
        # Ensure Normal (Continuous) Sampling mode is on.
        if self.Mode != 1:
            self.SetMode(1)
        self._writeReg([_REG_FIFO_CONFIG, _FIFO_CONFIG])
        self._writeReg([_REG_FIFO_CMD, _CMD_FIFO_START])

    # Stops writing to the FIFO queue.
    def FIFOStop(self):
        self._writeReg([_REG_FIFO_CMD, _CMD_FIFO_STOP])

    # Flushes the FIFO queue. All stored data is lost.
    def FIFOFlush(self):
        self._writeReg([_REG_CMD, _CMD_FIFO_FLUSH])

    # Returns the number of bytes used in the FIFO queue.
    @property
    def FIFOLength(self):
        buf = self._readReg(_REG_FIFO_LENGTH, 2)
        return buf[0] + buf[1] * 256

    # Reads all bytes in the FIFO queue.
    # Sensor data frames are parsed to retrieve
    # all stored uncompensated temperature and
    # pressure values. They are compensated and
    # returned as a list of tuples of actual values.
    @property
    def FIFORead(self):
        length = self.FIFOLength
        buf = self._readReg(_REG_FIFO_DATA, length)
        i = 0
        data = []
        while i < length:
            if buf[i] == _FIFO_SENSOR_FRAME:
                temperature = buf[i+1] + buf[i+2]*256 + buf[i+3]*65536
                pressure = buf[i+4] + buf[i+5]*256 + buf[i+6]*65536
                i += 7
                data.append(self._Compensate(temperature, pressure))
            else:
                i += 1
        return data

    # Returns True if the FIFO queue is full.
    @property
    def IsFIFOFull(self):
        buf = self._readReg(_REG_INT_STATUS, 1)
        return (buf[0] & 0b10) == 0b10

# *******************************************
#             Altitude Calculations
# *******************************************

    # Calculate mean sea level pressure (MSLP)
    # If the altitude of the sensor is known then
    # the absolute pressure can be adjusted to its
    # equivalent sea level pressure.
    #
    # This is the pressure that is reported by
    # official weather services.
    def MSLP(self, Altitude=None):
        if Altitude == None:
            return None
        else:
            P0 = 1013.25
            a = 2.25577E-5
            b = 5.25588
            P = self.Reading[1]
            PS = P0 * (1 - a * Altitude) ** b
            offset = P0 - PS
            return P + offset

    # If pressure readings are taken at different
    # altitudes then this method will calculate
    # the difference between these two altitudes
    # in meters.
    def AltDiff(self, P1, P2):
        a = 0.1157227
        return (P1 - P2) / a

    # If the Mean Sea Level pressure is known
    # (usually obtained from the local weather service)
    # then this method will calculate the altitude
    # of the sensor in meters.
    # The sensor is read to obtain the absolute
    # pressure value.
    def Altitude(self, MSLP=None):
        if MSLP == None:
            return None
        else:
            p = self.P
            a = -2.25577E-5
            b = 0.1902631
            h = (((p/MSLP) ** b) - 1) / a
            return int(round(h, 0))

# *******************************************
#              Private Methods
# *******************************************

    # Convert uncompensated temperature and pressure
    # to actual (compensated) values.
    def _Compensate(self, temperature, pressure):
        # Calculate actual temperature.
        pd1 = temperature - 256 * self.T1
        pd2 = self.T2 * pd1
        pd3 = pd1 * pd1
        pd4 = pd3 * self.T3
        pd5 = (pd2 * 262144) + pd4
        pd6 = pd5 / 4294967296
        t_lin = pd6
        comp_temp = (pd6 * 25) / 16384

        # Calculate actual pressure
        pd1 = t_lin * t_lin
        pd2 = pd1 / 64
        pd3 = (pd2 * t_lin) / 256
        pd4 = (self.P8 * pd3) / 32
        pd5 = self.P7 * pd1 * 16
        pd6 = self.P6 * t_lin * 4194304
        offset = (self.P5 * 140737488355328) + pd4 + pd5 + pd6
        pd2 = (self.P4 * pd3) / 32
        pd4 = (self.P3 * pd1) * 4
        pd5 = (self.P2 - 16384) * t_lin * 2097152
        sensitivity = ((self.P1 - 16384) * 70368744177664) + pd2 + pd4 + pd5
        pd1 = (sensitivity / 16777216) * pressure
        pd2 = self.P10 * t_lin
        pd3 = pd2 + (65536 * self.P9)
        pd4 = pd3 * pressure / 8192
        pd5 = (pressure * pd4) / 512
        pd6 = pressure * pressure
        pd2 = (self.P11 * pd6) / 65536
        pd3 = pd2 * pressure / 128
        pd4 = (offset / 4) + pd1 +pd5 +pd3
        comp_press = pd4 *25 / 1099511627776
        return comp_temp / 100, comp_press / 10000

    # Get the trimming constants from NVM.
    def _Load_Calibration_Data(self):
        fmt = '<HHbhhbbHHbbhbb'
        coeff = self._readReg(_REG_COEFF, 21)
        coeff = unpack(fmt, coeff)
        self.T1 = coeff[0]
        self.T2 = coeff[1]
        self.T3 = coeff[2]
        self.P1 = coeff[3]
        self.P2 = coeff[4]
        self.P3 = coeff[5]
        self.P4 = coeff[6]
        self.P5 = coeff[7]
        self.P6 = coeff[8]
        self.P7 = coeff[9]
        self.P8 = coeff[10]
        self.P9 = coeff[11]
        self.P10 = coeff[12]
        self.P11 = coeff[13]

    # Writes one or more bytes to register.
    # Bytes is expected to be a list.
    # First element is the register address.
    def _writeReg(self, Bytes):
        i2c.writeto(self.ADDR, bytes(Bytes))

    # Read a given number of bytes from
    # a register.
    def _readReg(self, Reg, Num):
        # Write the register address, then read bytes from device
        i2c.writeto(self.ADDR, bytes([Reg]))
        return i2c.readfrom(self.ADDR, Num)

    # Performs a soft reset.
    # All registers are loaded with power-on values.
    def _Reset(self):
        self._writeReg([_REG_CMD, _CMD_RESET])

# *******************************************
#              Derived Classes
# *******************************************

class BMP390(BMP3XX):
    @property
    def Type(self):
        return 'BMP390'

    # Chip revision number
    @property
    def RevID(self):
        id = self._readReg(_REG_REV_ID, 1)
        return hex(id[0])

class BMP388(BMP3XX):
    @property
    def Type(self):
        return 'BMP388'

       