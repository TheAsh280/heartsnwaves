// STM32F401 Hardware DSP & Sensor Stream
#define ECG_PIN PA0
#define TEMP_PIN PA1

// DSP Filter Variables (FPU Optimized)
const int FILTER_WINDOW = 10;
float ecgBuffer[FILTER_WINDOW] = {0.0};
int bufferIndex = 0;

void setup() {
  // Initialize Serial communication at 115200 baud
  Serial.begin(115200);
  
  pinMode(ECG_PIN, INPUT);
  pinMode(TEMP_PIN, INPUT);
}

// DSP Function: Moving Average Filter utilizing FPU
float applyDSPFilter(float rawSignal) {
  ecgBuffer[bufferIndex] = rawSignal;
  bufferIndex = (bufferIndex + 1) % FILTER_WINDOW;
  
  float sum = 0.0;
  for (int i = 0; i < FILTER_WINDOW; i++) {
    sum += ecgBuffer[i];
  }
  return sum / (float)FILTER_WINDOW; // Floating point arithmetic
}

void loop() {
  // 1. Read raw ECG value (12-bit ADC: 0 to 4095)
  float rawECG = analogRead(ECG_PIN);
  
  // 2. Apply DSP Filter
  float filteredECG = applyDSPFilter(rawECG);
  
  // 3. Simple Heart Rate Estimate from peak (BPM mapping)
  float estimatedBPM = map(filteredECG, 0, 4095, 50, 140);
  
  // 4. Read Temperature (Simulated or Analog scaling)
  float rawTemp = analogRead(TEMP_PIN);
  float temperatureC = 35.0 + (rawTemp / 4095.0) * 5.0; // Scaled between 35.0°C and 40.0°C

  // 5. Output CSV format to Serial: "BPM,Temperature"
  Serial.print(estimatedBPM, 1);
  Serial.print(",");
  Serial.println(temperatureC, 1);

  delay(100); // 10Hz sample rate for smooth stream
}