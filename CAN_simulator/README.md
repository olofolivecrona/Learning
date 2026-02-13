# Learning
A place for small projects created as part of learning new things.

## CAN bus simulation

This workspace includes a terminal-based CAN bus simulator in `can_simulator.py`.

### Features

- Enter and send CAN frames onto a simulated bus
- Interpret and list CAN messages observed on the bus
- Continuously show whether the bus is currently HIGH (recessive) or LOW (dominant)

### What a CAN frame consists of

In this simulator, a CAN data frame is built from the same core parts as a classical CAN frame:

- **SOF (Start Of Frame)**: 1 dominant bit (`0`) that marks frame start.
- **Arbitration field (Identifier)**:
	- **Standard frame**: 11-bit identifier.
	- **Extended frame**: 29-bit identifier.
- **Control field**:
	- Includes frame/control bits and the **DLC** (Data Length Code), which tells how many data bytes follow.
- **Data field**:
	- 0 to 8 data bytes (in this simulator, entered as hex after `#`).
- **CRC + ACK + EOF/Intermission**:
	- Trailer bits used for integrity, acknowledgment, and frame end.

The command format is:

- `send ID#DATA`
	- `ID` is hexadecimal CAN identifier (11-bit or 29-bit)
	- `DATA` is hexadecimal payload (`00` to 8 bytes, so up to 16 hex chars)

Example:

- `send 123#11223344`
	- ID = `0x123`
	- DLC = `4`
	- Data bytes = `11 22 33 44`

### Run

```powershell
python .\can_simulator.py
```

### Commands

- `send ID#DATA` — send a CAN frame (hex)
	- Example: `send 123#11223344`
	- Example (extended ID): `send 18DAF110#022105`
- `interpret` — decode/list frames seen on the bus
- `status` — show current bus level
- `help` — list commands
- `quit` — exit
