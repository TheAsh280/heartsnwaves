import time
import random
import numpy as np
import serial
from sklearn.tree import DecisionTreeClassifier

# ==========================================
# 1. CONFIGURATION & AI MODEL INITIALIZATION
# ==========================================
# Set to False when the STM32 is plugged in
SIMULATION_MODE = False  
SERIAL_PORT = 'COM7'    # Replace with your actual COM port (e.g., 'COM3', 'COM4')
BAUD_RATE = 115200

# Training data features: [Heart Rate (BPM), Temp (°C), Sim SpO2 (%), Sim Systolic BP]
# Target Risk Levels: 0 = Normal, 1 = Warning, 2 = High Risk
X_train = [
    [72, 36.6, 98, 120],  # Normal
    [65, 36.8, 99, 115],  # Normal
    [110, 38.5, 95, 135], # Warning (Fever/Elevated HR)
    [50, 35.5, 93, 100],  # Warning (Hypothermia/Low HR)
    [140, 39.2, 88, 150], # High Risk
    [45, 35.0, 85, 90]    # High Risk
]
y_train = [0, 0, 1, 1, 2, 2]

# Train Decision Tree Model
classifier = DecisionTreeClassifier()
classifier.fit(X_train, y_train)

risk_labels = {0: "NORMAL", 1: "WARNING", 2: "CRITICAL RISK"}

# ==========================================
# 2. DIGITAL TWIN PARAMETER ESTIMATION
# ==========================================
def compute_digital_twin_metrics(bpm, temp):
    """
    Simulates extra physiological parameters (SpO2 & Blood Pressure)
    based on real-time ECG and Temperature inputs.
    """
    spo2 = max(85.0, min(100.0, 99.0 - (temp - 37.0) * 2 - random.uniform(0, 1)))
    systolic_bp = 100 + (bpm - 60) * 0.5 + random.uniform(-3, 3)
    return round(spo2, 1), round(systolic_bp, 1)

# ==========================================
# 3. MAIN LIVE/SIMULATION DATA PIPELINE
# ==========================================
def run_pipeline():
    print("--- Digital Twin Patient Health Monitor ---")
    
    ser = None
    if not SIMULATION_MODE:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
            print(f"Connected to STM32 on {SERIAL_PORT} @ {BAUD_RATE} baud.")
        except Exception as e:
            print(f"Serial Connection Error: {e}")
            print("Switching back to Simulation Mode...")
            return

    while True:
        try:
            if SIMULATION_MODE:
                bpm = round(random.uniform(60, 120), 1)
                temp = round(random.uniform(36.5, 39.0), 1)
                time.sleep(1)
            else:
                # Read incoming line from STM32 ("BPM,Temperature")
                raw_line = ser.readline().decode('utf-8').strip()
                if not raw_line:
                    continue
                parts = raw_line.split(',')
                if len(parts) != 2:
                    continue
                bpm = float(parts[0])
                temp = float(parts[1])

            # Calculate Digital Twin derived parameters
            spo2, bp = compute_digital_twin_metrics(bpm, temp)
            
            # AI Inference
            features = np.array([[bpm, temp, spo2, bp]])
            prediction = classifier.predict(features)[0]
            status = risk_labels[prediction]
            
            # Display Diagnostic
            print(f"[LIVE RECV] HR: {bpm} BPM | Temp: {temp}°C | Est. SpO2: {spo2}% | Est. BP: {bp} mmHg")
            print(f"[AI DIAGNOSTIC] Patient Status: {status}\n")

        except KeyboardInterrupt:
            print("\nStopping Health Monitor.")
            if ser and ser.is_open:
                ser.close()
            break

if __name__ == "__main__":
    run_pipeline()