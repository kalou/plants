CC=avr-gcc
# Flags for attiny85
CFLAGS=-Wall -g -Os -mmcu=attiny85 -fverbose-asm -Itinycan -DDEBUG
LDFLAGS=-mmcu=attiny85 -Ltinycan
# Adapt to your programmer type & device info:
DUDEFLAGS=-cusbtiny -pt85
OBJS=avr.o tinycan/can.o

%.hex: %
	avr-objcopy -R .eeprom -O ihex $< $@

all: avr.hex

avr: $(OBJS)

avr-install: avr.hex
	# Fuse 0x5f: defaults + reset disable: This will make
	# further flashing require a high-voltage programmer, use
	# only with final working version if you don´t have one.
	# avrdude $(DUDEFLAGS) -U flash:w:$< -U hfuse:w:0x5f:m
	avrdude $(DUDEFLAGS) -U flash:w:$<

clean:
	rm -f avr avr.hex $(OBJS) avr.elf
