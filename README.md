# Event-Driven ECG Intelligence & Digital Twin System

An event-driven health monitoring system integrating an **STM32F401CCU6 (BlackPill)** board, an **AD8232 ECG sensor**, and a **Python Digital Twin** running a Machine Learning classifier.

## Features
- **Embedded DSP**: Moving average filter on STM32 using floating-point processing.
- **Real-Time Data Transport**: USB-Serial streaming at 115200 baud.
- **AI Health Classification**: Decision Tree model classifying patient risk (`NORMAL`, `WARNING`, `CRITICAL RISK`).
- **Digital Twin Parameter Estimation**: Simulates secondary physiological metrics (SpO2 & BP) based on live heart rate and temperature.

## Project Structure
- `digital_twin.py`: Python script running the machine learning model and serial reader.
- `firmware.ino`: C++ embedded code for signal reading and DSP processing.