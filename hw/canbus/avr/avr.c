#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>

#include "can.h"
#include "plants.h"

// PB0, PDIP pin 5 turns on transistor to sensor's +5v.
// The sensor output is measured at ADC PB1 (ADC1), which
// is also the pin used for CAN transceiver TX by canbus.
#define DD_SENSOR_VCC (1 << DDB0)
#define P_SENSOR_VCC (1 << PB0)
#define SENSOR_on() do { PORTB |= P_SENSOR_VCC; } while(0)
#define SENSOR_off() do { PORTB &= ~P_SENSOR_VCC; } while(0)

#define DD_SWITCH_VCC (1 << DDB3)
#define P_SWITCH_VCC (1 << PB3)
#define SWITCH_on() do {  PORTB |= P_SWITCH_VCC; } while(0)
#define SWITCH_off() do {  PORTB &= ~P_SWITCH_VCC; } while(0)


static volatile bool adc_complete = false;
ISR(ADC_vect)
{
	adc_complete = true;
}

int16_t read_adc(int adc)
{
	int16_t reading, avg=0;

	/* Enable sleep mode, with ADC noise reduction,
	 * enable ADC and the ADC completion interrupt.
	 */
	MCUCR = (1<<SE) | (1<<SM0); 

	if (adc == 15) {
		// For temperature reading:
		// MUX[3:0] = 0b1111 selecting ADC4
		// REFS[2:0] = 0b010 selecting internal 1.1v ref
		ADMUX = (1<<REFS1) | 15;
	} else {
		// MUX[3:0] = 0b001, ADC1 (PB2)
		// REFS[2:0] = 0b000, Vcc reference
		ADMUX = adc & 3;
	}
	ADCSRA = (1<<ADEN) | (1<<ADIE) | (1<<ADIF) | 7; // Enable ADC, with interrupt, prescaler: ~60khz

	sei();

	// Perform moving average over 16 readings.
	for (int i = 0; i <16; i++) {
		adc_complete = false;
		sleep_cpu();
		while(!adc_complete);

		reading = ADCL;
		reading |= ADCH << 8;

		if (i == 0)
			continue;
		else if (i == 1)
			avg = reading;
		else
			avg = avg + ((reading - avg) / (i+1));
	}

	// disable ADC to save power
	ADCSRA &= ~(1<<ADEN);

	return avg;
}

uint16_t read_temperature()
{
	return read_adc(15);
}

uint16_t read_sensor()
{
	SENSOR_on();
	// Disable transceiver and set TXD low for measure.
	STBY_high();
	DDRB &= ~(1<<DD_TXD);
	TXD_low();

	// Give sensor some warmup delay before we measure it.
	can_delay_ms(500);

	uint16_t v = read_adc(1);

	// Restore TXD & transceiver.
	SENSOR_off();
	TXD_high();
	DDRB |= (1<<DD_TXD);
	STBY_low();

	return v;
}

/* To turn RST port into a button without having
 * to reprogram the fuse, we use a well-known
 * divider trick.
 *
 * From datasheet R-rst is a pullup between 30k & 60k.
 * With a ~47k resistor to GND, ADC0 should read
 * somewhere between 400 and 700.
 */
bool is_button()
{
	uint16_t v = read_adc(0);
	return (v > 350 && v < 750);
}

bool check_reset_sequence()
{
	uint8_t cnt = 0;
	do {
		// Signal that we detect it
		if (is_button() && (cnt%20 == 0)) {
			SENSOR_on();
			can_delay_ms(100);
			SENSOR_off();
		}
		if (cnt++ > 200)
			return true;
	} while(is_button());
	return false;
}

void save_config(plants_config_t *conf)
{
	conf->crc = 0;
	conf->crc = compute_crc(conf, sizeof(conf));

	EECR = (0<<EEPM1)|(0<<EEPM0);
	for (int i = 0; i < sizeof(plants_config_t); i++) {
		EEAR = i;
		EEDR = *((char *) conf+i);
		EECR |= (1<<EEMPE);
		EECR |= (1<<EEPE);

		while (EECR & (1<<EEPE));
	}
}

bool load_config(plants_config_t *conf)
{
	char *p = (char *) conf;
	uint16_t crc;

	for (int i=0; i < sizeof(plants_config_t); i++) {
		EEAR = i;
		EECR |= (1<<EERE);
		*p++ = EEDR;
	}

	crc = conf->crc;
	conf->crc = 0;
	if (compute_crc(conf, sizeof(conf)) == crc)
		return true;
	return false;
}

void perform_reconfig(plants_config_t *conf)
{
	int attempt = 0;
	can_header_t *c;

	for(;;) {
		// Shortly enable sensor to signal reset via LED.
		SENSOR_on();
		if (!(attempt++ % 5))
			can_request(PLANTS_AUTOCONF_ID, 0);
		c = can_receive(200);
		SENSOR_off();
		if (c && c->id == PLANTS_AUTOCONF_ID && !c->rtr) {
			// This contains our ID
			conf->id = *((uint32_t *) c->data) & 0x1fffffff;
			// Attempt to publish to it. If we get an
			// ACK, we own it.
			if (can_send(conf->id, "random", 6) == 0) {
				save_config(conf);
				return;
			}
		}
	}
}

int main(void)
{
	plants_config_t conf;

	DDRB = DD_SENSOR_VCC | DD_SWITCH_VCC;

	// Disable digital input on TX and RST, used as ADC
	DIDR0 = (1<<ADC1D) | (1<<ADC0D);

	// Tiny power savings. Most savings
	// are done by sleeping.
	PRR |= (1<<PRTIM1) | (1<<PRUSI);

	can_init();

	// Read sensor at boot to indicate firmware startup.
	read_sensor();

	if (!load_config(&conf)) {
		can_send(0x123, (char *) &conf, sizeof(conf));
		perform_reconfig(&conf);
	}

	for (;;) {
		can_header_t *c;

		do {
			c = can_receive(500);
			if (check_reset_sequence()) {
				DEBUG_high();
				perform_reconfig(&conf);
				DEBUG_low();
			}
		} while(!c);


		if ((c->id == conf.id) || (c->id == PLANTS_ALL_SENSORS_ID)) {
			if (c->rtr) {
				uint16_t sensor_data = read_sensor();
				can_send(conf.id, (char *)&sensor_data, 2);
			} else if (c->len == 2 && c->data[0] == PLANTS_CMD_SWITCH) {
				switch(c->data[1]) {
					case PLANTS_CMD_SWITCH_ON:
						if (c->id == conf.id)
							SWITCH_on();
						break;
					case PLANTS_CMD_SWITCH_OFF:
						SWITCH_off();
						break;
				}
			}
		}
	}
}
