from dataclasses import dataclass
from typing import Tuple, Dict
import struct
import posixpath


import gdb


def exec_gdb_command(command):
    gdb.execute(command)


@dataclass
class AppState:
    name: str
    text_address: int = 0
    entry_address: int = 0
    other_sections: Dict[str, int] = None
    debug_link_elf: str = ""
    debug_link_crc: int = 0

    def __post_init__(self):
        if self.other_sections is None:
            self.other_sections = {}

    def get_gdb_load_command(
        self, elf_path="build/latest/applications/.extapps"
    ) -> str:
        load_path = (
            posixpath.join(elf_path, self.debug_link_elf)
            if elf_path
            else self.debug_link_elf
        )
        load_command = (
            f"add-symbol-file -readnow {load_path} 0x{self.text_address:08x} "
        )
        load_command += " ".join(
            f"-s {name} 0x{address:08x}"
            for name, address in self.other_sections.items()
        )
        return load_command

    def get_gdb_unload_command(self) -> str:
        return f"remove-symbol-file -a 0x{self.text_address:08x}"

    def is_loaded_in_gdb(self, gdb_app) -> bool:
        # Avoid constructing full app wrapper for comparison
        return self.entry_address == int(gdb_app["entry"])

    @staticmethod
    def parse_debug_link_data(section_data) -> Tuple[str, int]:
        # Debug link format: a null-terminated string with debuggable file name
        # Padded with 0's to multiple of 4 bytes
        # Followed by 4 bytes of CRC32 checksum of that file
        elf_name = section_data[:-4].decode("utf-8").split("\x00")[0]
        crc32 = struct.unpack("<I", section_data[-4:])[0]
        return (elf_name, crc32)

    @staticmethod
    def from_gdb(gdb_app: "AppState") -> "AppState":
        state = AppState(str(gdb_app["manifest"]["name"].string()))
        state.entry_address = int(gdb_app["entry"])

        app_state = gdb_app["state"]
        if debug_link_size := int(app_state["debug_link_size"]):
            debug_link_data = (
                gdb.selected_inferior()
                .read_memory(int(app_state["debug_link"]), debug_link_size)
                .tobytes()
            )
            state.debug_link_elf, state.debug_link_crc = AppState.parse_debug_link_data(
                debug_link_data
            )

        for idx in range(app_state["mmap_entry_count"]):
            mmap_entry = app_state["mmap_entries"][idx]
            section_name = mmap_entry["name"].string()
            section_addr = int(mmap_entry["address"])
            if section_name == ".text":
                state.text_address = section_addr
            else:
                state.other_sections[section_name] = section_addr

        return state


class FlipperAppDebugHelper:
    def __init__(self):
        self.app_ptr = None
        self.app_type_ptr = None
        self.current_app: AppState = None

    def attach_fw(self):
        self.app_ptr = gdb.lookup_global_symbol("last_loaded_app")
        self.app_type_ptr = gdb.lookup_type("FlipperApplication").pointer()
        self._check_app_state()

    def _check_app_state(self):
        app_ptr_value = self.app_ptr.value()
        if not app_ptr_value and self.current_app:
            self._unload_debug_elf()
        elif app_ptr_value:
            loaded_app = app_ptr_value.cast(self.app_type_ptr).dereference()
            if self.current_app:
                if not self.current_app.is_loaded_in_gdb(loaded_app):
                    self._unload_debug_elf()
                    self._load_debug_elf(loaded_app)
            else:
                self._load_debug_elf(loaded_app)

    def _unload_debug_elf(self):
        gdb.execute(self.current_app.get_gdb_unload_command())
        self.current_app = None

    def _load_debug_elf(self, app_object):
        self.current_app = AppState.from_gdb(app_object)
        gdb.execute(self.current_app.get_gdb_load_command())

    def handle_stop(self, event):
        self._check_app_state()


helper = FlipperAppDebugHelper()
helper.attach_fw()
print("Support for Flipper external apps debug is enabled")

gdb.events.stop.connect(helper.handle_stop)
