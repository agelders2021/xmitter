#!/usr/bin/env python3
"""
tinysa_avg.py - Live averaged spectrum display for the tinySA Ultra.

Repeatedly runs 'scanraw' sweeps over USB serial, accumulates a running
average, and shows a live matplotlib plot with the latest single sweep
(faint) and the running average (bold).

Averaging is done in linear power (mW) by default, which is the correct
way to average power measurements; use --db-average to average the dBm
values directly (what some analyzers call "log/video averaging" - it
reads a few dB lower on noise).

Usage examples:
    python tinysa_avg.py -s 13.9e6 -e 14.1e6 -p 290 -n 20
    python tinysa_avg.py -s 0 -e 30e6 -p 450 -r 10000      # 10 kHz RBW
    python tinysa_avg.py -s 14e6 -e 14.35e6 --db-average --csv out.csv

Requires: pyserial, numpy, matplotlib
"""

import argparse
import struct
import sys
import time

import numpy as np
import serial
from serial.tools import list_ports

import matplotlib.pyplot as plt

# tinySA USB identifiers (same for all models)
VID = 0x0483
PID = 0x5740

# dBm = raw/32 - SCALE.  tinySA (original) = 128, tinySA4 / Ultra = 174.
SCALE_ULTRA = 174
SCALE_BASIC = 128


def find_port() -> str:
    for dev in list_ports.comports():
        if dev.vid == VID and dev.pid == PID:
            return dev.device
    raise OSError("No tinySA found. Is it plugged in (and not held open by tinySA-App)?")


class TinySA:
    def __init__(self, port: str, scale: int = SCALE_ULTRA):
        self.ser = serial.Serial(port, baudrate=115200, timeout=2)
        self.scale = scale
        self._drain()

    def _drain(self):
        time.sleep(0.1)
        self.ser.reset_input_buffer()

    def command(self, cmd: str) -> bytes:
        """Send a text command, return everything up to the 'ch> ' prompt."""
        self.ser.write((cmd + "\r").encode())
        self.ser.read_until(b"\r\n")          # discard command echo
        return self.ser.read_until(b"ch> ")

    def set_rbw(self, rbw_hz: float | None):
        if rbw_hz is None:
            self.command("rbw auto")
        else:
            rbw_k = min(max(rbw_hz / 1e3, 0.2), 850)  # Ultra range ~200 Hz..850 kHz
            self.command(f"rbw {rbw_k:g}")

    def scanraw(self, f_start: float, f_stop: float, points: int,
                timeout: float) -> np.ndarray:
        """One sweep; returns power in dBm as a numpy array of length 'points'."""
        self.ser.timeout = timeout
        self.ser.write(f"scanraw {int(f_start)} {int(f_stop)} {points}\r".encode())
        self.ser.read_until(b"{")             # skip echo, find start of binary block

        need = 3 * points                      # 'x' + uint16 LE per point
        raw = self.ser.read(need)
        if len(raw) != need:
            raise TimeoutError(
                f"Short read ({len(raw)}/{need} bytes). Try a longer --timeout "
                f"or wider RBW.")
        self.ser.read_until(b"ch> ")           # consume trailing '}' + prompt

        vals = struct.unpack("<" + "xH" * points, raw)
        return np.asarray(vals, dtype=np.float64) / 32.0 - self.scale

    def close(self):
        try:
            self.command("rbw auto")           # restore normal screen behavior
        except Exception:
            pass
        self.ser.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1],
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("-d", "--device", help="serial port (default: autodetect)")
    ap.add_argument("-s", "--start", type=float, default=13.9e6, help="start freq, Hz")
    ap.add_argument("-e", "--end", type=float, default=14.1e6, help="stop freq, Hz")
    ap.add_argument("-p", "--points", type=int, default=290, help="sweep points")
    ap.add_argument("-r", "--rbw", type=float, default=None,
                    help="resolution bandwidth in Hz (default: auto)")
    ap.add_argument("-n", "--sweeps", type=int, default=0,
                    help="number of sweeps to average (0 = run until window closed)")
    ap.add_argument("--db-average", action="store_true",
                    help="average dBm values instead of linear power")
    ap.add_argument("--basic", action="store_true",
                    help="original tinySA (not Ultra): use scale 128")
    ap.add_argument("--timeout", type=float, default=15.0,
                    help="serial timeout per sweep, seconds")
    ap.add_argument("--csv", help="write final averaged trace to this CSV file")
    args = ap.parse_args()

    port = args.device or find_port()
    print(f"Connecting to {port} ...")
    sa = TinySA(port, SCALE_BASIC if args.basic else SCALE_ULTRA)
    sa.set_rbw(args.rbw)

    freqs = np.linspace(args.start, args.end, args.points)
    fmhz = freqs / 1e6

    # Running-average accumulator
    acc = np.zeros(args.points)
    count = 0

    plt.ion()
    fig, ax = plt.subplots(figsize=(10, 6))
    (line_last,) = ax.plot(fmhz, np.full(args.points, np.nan),
                           color="0.75", lw=0.8, label="last sweep")
    (line_avg,) = ax.plot(fmhz, np.full(args.points, np.nan),
                          color="tab:blue", lw=1.6, label="average")
    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel("Power (dBm)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    fig.canvas.manager.set_window_title("tinySA averaged scan")

    try:
        while plt.fignum_exists(fig.number):
            dbm = sa.scanraw(args.start, args.end, args.points, args.timeout)
            count += 1

            if args.db_average:
                acc += dbm
                avg = acc / count
            else:
                acc += 10.0 ** (dbm / 10.0)          # dBm -> mW, accumulate
                avg = 10.0 * np.log10(acc / count)   # mean mW -> dBm

            line_last.set_ydata(dbm)
            line_avg.set_ydata(avg)
            ax.relim(); ax.autoscale_view()
            ax.set_title(f"{fmhz[0]:.4f}-{fmhz[-1]:.4f} MHz   "
                         f"sweeps averaged: {count}")
            fig.canvas.draw_idle()
            plt.pause(0.05)

            if args.sweeps and count >= args.sweeps:
                break
    except KeyboardInterrupt:
        pass
    finally:
        sa.close()

    if count == 0:
        print("No sweeps completed.")
        return

    print(f"Averaged {count} sweeps.")
    if args.csv:
        avg = (acc / count) if args.db_average else 10.0 * np.log10(acc / count)
        with open(args.csv, "w") as f:
            f.write("freq_hz,dbm_avg\n")
            for fr, db in zip(freqs, avg):
                f.write(f"{fr:.0f},{db:.2f}\n")
        print(f"Wrote {args.csv}")

    # Keep the final plot on screen until closed
    plt.ioff()
    if plt.fignum_exists(fig.number):
        plt.show()


if __name__ == "__main__":
    main()
