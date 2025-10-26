# MEMS Micromanipulator PID Tuner

A PID control system for MEMS-based micromanipulation with Arduino firmware and MATLAB/Simulink simulation.

## Project Structure

```
mems-pid-tuner/
├── firmware/
│   ├── arduino_pid.ino        # Arduino firmware for PID control of piezo stage
│   └── platformio.ini         # PlatformIO configuration
├── matlab_sim/
│   └── mems_model.slx         # Simulink model of MEMS cantilever
├── gui/
│   ├── src/
│   │   └── App.py             # Python GUI for PID tuning and data visualization
│   └── requirements.txt       # Python dependencies (pyserial, PyQt5)
├── README.md
└── datasheet_parser.py        # Script to extract parameters from a dummy datasheet
```

## Overview

PID control system for precise MEMS manipulation with real-time tuning interface and simulation validation.

## License

MIT License
