#include "random_name.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <furi.h>

void set_random_name(char* name, uint8_t max_name_size) {
    const char* prefix[] = {
        "ancient",     "hollow",    "strange",    "disappeared", "unknown",
        "unthinkable", "unnamable", "nameless",   "my",          "concealed",
        "forgotten",   "hidden",    "mysterious", "obscure",     "random",
        "remote",      "uncharted", "undefined",  "untravelled", "untold",
    };

    const char* suffix[] = {
        "door",
        "entrance",
        "doorway",
        "entry",
        "portal",
        "entree",
        "opening",
        "crack",
        "access",
        "corridor",
        "passage",
        "port",
    };
    uint8_t prefix_i = rand() % COUNT_OF(prefix);
    uint8_t suffix_i = rand() % COUNT_OF(suffix);

    snprintf(name, max_name_size, "%s_%s", prefix[prefix_i], suffix[suffix_i]);
    // Set first symbol to upper case
    name[0] = name[0] - 0x20;
}
