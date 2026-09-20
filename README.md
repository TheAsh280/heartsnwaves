**Hearts'n'Waves — 3-Level Event-Driven ECG Intelligence & Digital Twin**

A real-time embedded healthcare monitoring system powered by an STM32 micro-controller and a Python Digital Twin desktop client. The system captures electrocardiogram (ECG) signals, executes DSP and rhythm classification on-chip, streams telemetry over UART, and synthesizes a full clinical display with calculated physiological metrics.

**System Architecture**

[ AD8232 ECG Sensor ] ───> [ STM32 Hardware Timer Interrupt (200 Hz) ]
                                      │
 ┌────────────────────────────────────┴────────────────────────────────────┐
 │  ON-CHIP EMBEDDED PIPELINE (firmware.ino)                               │
 │                                                                         │
 │  • Level 0: IIR Bandpass Filter (Baseline Wander & Noise Cancellation)  │
 │  • Level 1: Pan-Tompkins Algorithm (Derivative, MWI, R-Peak Detection)  │
 │  • Level 1: HRV Calculation (RMSSD over 5-Beat RR Window)               │
 │  • Level 2: Decision Tree Rhythm Classifier (NORMAL / WARNING / RISK)   │
 └────────────────────────────────────┬────────────────────────────────────┘
                                      │  115200 Baud UART
                                      ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │  PYTHON DIGITAL TWIN GUI (digital_twin.py)                              │
 │                                                                         │
 │  • Real-Time Data Parsing (Serial Receiver)                             │
 │  • Phase-Locked P-QRS-T Waveform Synthesizer (Gaussian Model)           │
 │  • Secondary Parameter Estimation (SpO2 & Systolic Blood Pressure)      │
 │  • 30 FPS Throttled Matplotlib Clinical ECG Strip Display               │
 └─────────────────────────────────────────────────────────────────────────┘


**Python Digital Twin Client (digital_twin.py)**

`Real-Time Telemetry Receiver`: Parses 5-value CSV streams arriving over 115200 baud serial communication (COM7).   
`Phase-Locked Waveform Synthesis`: Generates mathematical Gaussian-driven P-QRS-T electrocardiogram curves synchronized in real-time to the patient's actual heart rate.   
`Physiological Metric Estimation`: Calculates estimated Oxygen Saturation (SpO2) and Systolic Blood Pressure (BP) dynamically from heart rate and body temperature data.   
Clinical ECG Strip Visualization: Renders a 4-second scrolling graph window styled like medical grid paper.   
Throttled Render Engine: Frame-throttled at 30 FPS to ensure smooth rendering and eliminate OS lag.   
Offline Simulation Mode: Toggling SIMULATION_MODE = True allows GUI testing without physical hardware connected.
