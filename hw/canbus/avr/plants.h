#ifndef _PLANTS_H
#define _PLANTS_H

typedef struct plants_config_ {
	uint32_t id;
	uint16_t crc;
} plants_config_t;

// Bcast high priority to e.g. turn things off
#define PLANTS_ALL_SENSORS_ID 0x01
// Bcast used to get an ID at sensor reset
#define PLANTS_AUTOCONF_ID 0x2a

#define PLANTS_CMD_SWITCH  0x12
#define PLANTS_CMD_SWITCH_ON 0x01
#define PLANTS_CMD_SWITCH_OFF 0x00

#endif
