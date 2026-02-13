from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime


DOMINANT = 0  # logical 0, bus LOW
RECESSIVE = 1  # logical 1, bus HIGH


@dataclass
class CANFrame:
    arbitration_id: int
    data: bytes
    is_extended_id: bool = False
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def dlc(self) -> int:
        return len(self.data)

    def to_wire_bits(self) -> list[int]:
        bits: list[int] = []

        bits.append(DOMINANT)  # SOF

        if self.is_extended_id:
            bits.extend(_int_to_bits(self.arbitration_id, 29))
            bits.extend([RECESSIVE, RECESSIVE])
        else:
            bits.extend(_int_to_bits(self.arbitration_id, 11))
            bits.extend([DOMINANT, DOMINANT, DOMINANT])

        bits.extend(_int_to_bits(self.dlc, 4))

        for byte in self.data:
            bits.extend(_int_to_bits(byte, 8))

        bits.extend([RECESSIVE] * 15)
        bits.extend([RECESSIVE, RECESSIVE, RECESSIVE])
        bits.extend([RECESSIVE] * 7)

        return bits

    def summary(self) -> str:
        frame_type = "Extended" if self.is_extended_id else "Standard"
        data_hex = self.data.hex().upper() or "<empty>"
        return (
            f"{frame_type} ID=0x{self.arbitration_id:X} "
            f"DLC={self.dlc} DATA={data_hex}"
        )


def _int_to_bits(value: int, width: int) -> list[int]:
    return [(value >> shift) & 1 for shift in range(width - 1, -1, -1)]


class CANBus:
    def __init__(self, bit_time: float = 0.03) -> None:
        self.bit_time = bit_time
        self.current_level = RECESSIVE
        self._tx_queue: queue.Queue[CANFrame] = queue.Queue()
        self._history: list[CANFrame] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    @property
    def level_name(self) -> str:
        return "HIGH (recessive)" if self.current_level == RECESSIVE else "LOW (dominant)"

    def enqueue(self, frame: CANFrame) -> None:
        self._tx_queue.put(frame)

    def history(self) -> list[CANFrame]:
        with self._lock:
            return list(self._history)

    def _worker(self) -> None:
        while self._running:
            try:
                frame = self._tx_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            bits = frame.to_wire_bits()
            print(f"\nTX -> {frame.summary()}")
            print("Bus trace:")

            for index, bit in enumerate(bits, start=1):
                self.current_level = RECESSIVE if bit else DOMINANT
                level_text = self.level_name
                print(f"  bit {index:03d}: {bit} => {level_text}")
                time.sleep(self.bit_time)

            self.current_level = RECESSIVE
            with self._lock:
                self._history.append(frame)

            print(f"Frame complete. Bus state: {self.level_name}\n")
            self._tx_queue.task_done()


def parse_frame(raw: str) -> CANFrame:
    if "#" not in raw:
        raise ValueError("Use format ID#DATA, e.g. 123#112233")

    id_part, data_part = raw.split("#", 1)
    if not id_part:
        raise ValueError("Missing CAN identifier")

    frame_id = int(id_part, 16)
    is_extended = frame_id > 0x7FF

    if data_part:
        if len(data_part) % 2 != 0:
            raise ValueError("Data must have an even number of hex characters")
        if len(data_part) > 16:
            raise ValueError("Data length exceeds 8 bytes")
        data = bytes.fromhex(data_part)
    else:
        data = b""

    if is_extended and frame_id > 0x1FFFFFFF:
        raise ValueError("Extended ID must be <= 0x1FFFFFFF")
    if not is_extended and frame_id > 0x7FF:
        raise ValueError("Standard ID must be <= 0x7FF")

    return CANFrame(arbitration_id=frame_id, data=data, is_extended_id=is_extended)


def print_help() -> None:
    print(
        "Commands:\n"
        "  send ID#DATA   Send a CAN frame (hex), e.g. send 123#DEADBEEF\n"
        "  interpret      Decode and list messages seen on the bus\n"
        "  status         Show current bus voltage level (HIGH/LOW)\n"
        "  help           Show this help\n"
        "  quit           Exit\n"
    )


def interpret_messages(frames: list[CANFrame]) -> None:
    if not frames:
        print("No messages received on the bus yet.")
        return

    print("Decoded bus messages:")
    for index, frame in enumerate(frames, start=1):
        print(
            f"  {index:03d}. {frame.timestamp.strftime('%H:%M:%S')} | {frame.summary()}"
        )


def main() -> None:
    bus = CANBus(bit_time=0.02)
    bus.start()

    print("CAN Bus Simulator")
    print_help()

    try:
        while True:
            prompt = f"[BUS {bus.level_name}] > "
            command = input(prompt).strip()

            if not command:
                continue

            lowered = command.lower()
            if lowered in {"quit", "exit"}:
                break
            if lowered == "help":
                print_help()
                continue
            if lowered == "status":
                print(f"Current bus state: {bus.level_name}")
                continue
            if lowered == "interpret":
                interpret_messages(bus.history())
                continue
            if lowered.startswith("send "):
                payload = command[5:].strip()
                try:
                    frame = parse_frame(payload)
                except ValueError as error:
                    print(f"Invalid frame: {error}")
                    continue

                bus.enqueue(frame)
                print("Frame queued for transmission.")
                continue

            print("Unknown command. Type 'help' to see available commands.")
    finally:
        bus.stop()


if __name__ == "__main__":
    main()