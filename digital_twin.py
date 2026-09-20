import time
import random
import numpy as np
import serial
from collections import deque
import matplotlib.pyplot as plt

# ==========================================
# 1. CONFIGURATION & TELEMETRY SETUP
# ==========================================
SIMULATION_MODE = False    # Set to True to test without hardware
SERIAL_PORT = 'COM7'        # Update COM port if needed
BAUD_RATE = 115200

SAMPLING_RATE = 200         # 200 Hz sampling
WINDOW_SECONDS = 4          # 4-second clinical strip display
TOTAL_SAMPLES = SAMPLING_RATE * WINDOW_SECONDS

risk_labels = {0: "NORMAL", 1: "WARNING", 2: "CRITICAL RISK"}
risk_colors = {0: "#008000", 1: "#D97706", 2: "#DC2626"}

def compute_digital_twin_metrics(bpm, temp):
    spo2 = max(85.0, min(100.0, 99.0 - max(0.0, temp - 37.0) * 2 - random.uniform(0, 0.8)))
    systolic_bp = 100 + (bpm - 60) * 0.4 + random.uniform(-2, 2)
    return round(spo2, 1), round(systolic_bp, 1)

# ==========================================
# 2. P-QRS-T WAVEFORM SYNTHESIZER
# ==========================================
def get_pqrst_point(phase, is_connected):
    if not is_connected:
        return np.random.normal(0, 0.01)
    
    p = 0.12 * np.exp(-((phase - 0.12) / 0.022)**2)
    q = -0.12 * np.exp(-((phase - 0.22) / 0.007)**2)
    r = 1.20 * np.exp(-((phase - 0.24) / 0.008)**2)
    s = -0.30 * np.exp(-((phase - 0.26) / 0.010)**2)
    t = 0.22 * np.exp(-((phase - 0.45) / 0.045)**2)
    
    noise = np.random.normal(0, 0.015)
    return p + q + r + s + t + noise

# ==========================================
# 3. CLINICAL ECG STRIP GRAPHICAL MONITOR
# ==========================================
def run_pipeline():
    print("--- Hearts'n'Waves Live 3-Level Clinical ECG Monitor ---")
    
    ser = None
    if not SIMULATION_MODE:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.02)
            ser.reset_input_buffer()
            print(f"Connected to STM32 Level 2 UART on {SERIAL_PORT} @ {BAUD_RATE} baud.")
            print("-" * 60)
        except Exception as e:
            print(f"Serial Connection Error: {e}")
            return

    time_axis = np.linspace(0, WINDOW_SECONDS, TOTAL_SAMPLES)
    ecg_buffer = deque([0.0] * TOTAL_SAMPLES, maxlen=TOTAL_SAMPLES)

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.canvas.manager.set_window_title("Hearts'n'Waves — Clinical ECG Strip (3-Level Architecture)")
    
    paper_color = '#FFF2F4'
    fig.patch.set_facecolor(paper_color)
    ax.set_facecolor(paper_color)

    ax.minorticks_on()
    ax.grid(True, which='major', color='#FF6B81', linestyle='-', linewidth=0.8, alpha=0.7)
    ax.grid(True, which='minor', color='#FFA0B0', linestyle=':', linewidth=0.5, alpha=0.6)

    line_ecg, = ax.plot(time_axis, ecg_buffer, color='#0B0E14', lw=1.3)

    ax.set_ylabel("Voltage (mV)", fontsize=10, color='#800016', fontweight='bold')
    ax.set_xlabel("Time Window (Seconds)", fontsize=10, color='#800016', fontweight='bold')
    ax.set_ylim(-0.5, 1.5)
    ax.set_xlim(0, WINDOW_SECONDS)

    telemetry_box = ax.text(
        0.015, 0.88, "INITIALIZING CLINICAL MONITOR...", transform=ax.transAxes,
        fontsize=11, fontweight='bold', color='#111827',
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFFFFF", edgecolor="#FF6B81", alpha=0.95)
    )

    plt.tight_layout()
    plt.ion()
    plt.show(block=False)

    current_bpm = 72.0
    current_temp = 36.8
    embedded_rhythm_class = 0
    current_hrv = 35.0
    cardiac_phase = 0.0
    last_loop_time = time.time()
    last_hud_update = time.time()
    last_draw_time = time.time()

    while True:
        try:
            now = time.time()
            dt = now - last_loop_time
            last_loop_time = now

            if SIMULATION_MODE:
                current_bpm = round(75.0 + 8.0 * np.sin(now * 0.2) + random.uniform(-1, 1), 1)
                current_temp = 36.8
                current_hrv = round(35.0 + random.uniform(-2, 2), 1)
                embedded_rhythm_class = 0
            else:
                if ser.in_waiting > 0:
                    lines = ser.read_all().decode('utf-8', errors='ignore').strip().split('\n')
                    latest_line = lines[-1].strip()
                    parts = latest_line.split(',')
                    
                    if len(parts) >= 4:
                        try:
                            current_bpm = float(parts[1])
                            parsed_temp = float(parts[2])
                            current_temp = round(0.9 * current_temp + 0.1 * parsed_temp, 1)
                            embedded_rhythm_class = int(parts[3])
                            if len(parts) >= 5:
                                current_hrv = float(parts[4])
                        except ValueError:
                            pass

            is_connected = (current_bpm > 0.0)
            if is_connected:
                phase_velocity = current_bpm / 60.0
                cardiac_phase += phase_velocity * dt
                if cardiac_phase >= 1.0:
                    cardiac_phase -= 1.0
            else:
                cardiac_phase = 0.0

            val = get_pqrst_point(cardiac_phase, is_connected)
            ecg_buffer.append(val)

            # Throttled 30 FPS Render Execution (Fixes Laptop Lag & "Not Responding")
            if now - last_draw_time > 0.033:
                last_draw_time = now
                line_ecg.set_ydata(ecg_buffer)
                fig.canvas.draw_idle()
                fig.canvas.flush_events()

            if now - last_hud_update > 0.5:
                last_hud_update = now

                if not is_connected:
                    telemetry_box.set_text("STATUS: LEADS DISCONNECTED\nAttach wrist electrodes firmly.")
                    telemetry_box.set_color("#DC2626")
                else:
                    spo2, bp = compute_digital_twin_metrics(current_bpm, current_temp)
                    status_str = risk_labels.get(embedded_rhythm_class, "NORMAL")
                    status_color = risk_colors.get(embedded_rhythm_class, "#008000")

                    telemetry_box.set_text(
                        f"PATIENT STATUS (ON-CHIP L2): {status_str}\n"
                        f"HR: {current_bpm:.1f} BPM  |  HRV: {current_hrv:.1f} ms  |  SpO2: {spo2}%  |  Est. BP: {bp} mmHg  |  Temp: {current_temp:.1f}°C"
                    )
                    telemetry_box.set_color(status_color)

                    print(f"[UART EVENT] HR: {current_bpm:.1f} BPM | HRV: {current_hrv:.1f}ms | On-Chip Class: {status_str}")

            time.sleep(0.005)

        except KeyboardInterrupt:
            print("\nStopping Monitor.")
            if ser and ser.is_open:
                ser.close()
            plt.close('all')
            break
        except Exception:
            continue

if __name__ == "__main__":
    run_pipeline()