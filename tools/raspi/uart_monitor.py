#!/usr/bin/env python3
"""
Raw UART hex monitor — prints incoming bytes as hex to console.
Ctrl+C or 'q' to quit.
"""

import argparse
import select
import sys
import termios
import tty

import serial


def monitor(port, baud):
    ser = serial.Serial(port, baud, timeout=0.1)
    old = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        print(f"Monitoring {port} @ {baud} — press q or Esc to quit\n")
        while True:
            data = ser.read(64)
            if data:
                print(" ".join(f"{b:02X}" for b in data), flush=True)
            if select.select([sys.stdin], [], [], 0)[0]:
                ch = sys.stdin.read(1)
                if ch in ("q", "Q", "\x1b"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
        ser.close()
        print("\nStopped.")


def main():
    p = argparse.ArgumentParser(description="Raw UART hex monitor")
    p.add_argument("--port", default="/dev/serial0", help="Serial port (default: /dev/serial0)")
    p.add_argument("--baud", type=int, default=9600, help="Baud rate (default: 9600)")
    args = p.parse_args()
    monitor(args.port, args.baud)


if __name__ == "__main__":
    main()
