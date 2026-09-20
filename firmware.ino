// =============================================================
// THREE-LEVEL EVENT-DRIVEN EMBEDDED ECG ARCHITECTURE (STM32)
// =============================================================
#include <Arduino.h>

#define ECG_PIN PA0
#define TEMP_PIN PA1
#define LO_PLUS_PIN PA3
#define LO_MINUS_PIN PA2

volatile bool sampleReady = false;
volatile float rawECGValue = 0.0;

// Level 0: Bandpass Filter Memory
float bpf_x1 = 0, bpf_x2 = 0, bpf_y1 = 0, bpf_y2 = 0;

// Level 1: Pan-Tompkins State
float d_buf[5] = {0};
float mwi_buf[30] = {0};
int mwi_idx = 0;
float mwi_sum = 0.0;
float signalThreshold = 1800.0; // Higher noise floor

unsigned long lastRPeakTime = 0;
float currentBPM = 72.0;
float hrvRMSSD = 35.0;
unsigned long rrIntervals[5] = {800, 800, 800, 800, 800};
int rrIdx = 0;
int rhythmClass = 0; 

// --- LEVEL 2: ON-DEVICE DECISION TREE RHYTHM CLASSIFIER ---
int embeddedDecisionTree(float bpm, float temp, float hrv) {
  if (bpm <= 0.0) return 2; // Leads off
  if (bpm < 45.0 || bpm > 140.0 || temp > 39.0 || temp < 34.0) {
    return 2; // Critical Risk
  }
  if (bpm < 55.0 || bpm > 105.0 || temp > 37.8 || hrv < 15.0) {
    return 1; // Warning
  }
  return 0; // Normal
}

HardwareTimer *MyTim;

void Timer_Callback(void) {
  rawECGValue = analogRead(ECG_PIN);
  sampleReady = true;
}

void setup() {
  Serial.begin(115200);
  pinMode(ECG_PIN, INPUT);
  pinMode(TEMP_PIN, INPUT);
  pinMode(LO_PLUS_PIN, INPUT);
  pinMode(LO_MINUS_PIN, INPUT);
  analogReadResolution(12);

  #if defined(TIM3)
  MyTim = new HardwareTimer(TIM3);
  MyTim->setOverflow(200, HERTZ_FORMAT);
  MyTim->attachInterrupt(Timer_Callback);
  MyTim->resume();
  #endif
}

float runLevel0_Bandpass(float x) {
  float y = 0.2929 * x - 0.2929 * bpf_x2 + 0.5858 * bpf_y1 - 0.1716 * bpf_y2;
  bpf_x2 = bpf_x1; bpf_x1 = x;
  bpf_y2 = bpf_y1; bpf_y1 = y;
  return y;
}

bool runLevel1_PanTompkins(float ecgSignal, unsigned long now) {
  d_buf[4] = d_buf[3]; d_buf[3] = d_buf[2]; d_buf[2] = d_buf[1]; d_buf[1] = d_buf[0];
  d_buf[0] = ecgSignal;
  float deriv = (2.0 * d_buf[0] + d_buf[1] - d_buf[3] - 2.0 * d_buf[4]) / 8.0;

  float squared = deriv * deriv;

  mwi_sum -= mwi_buf[mwi_idx];
  mwi_buf[mwi_idx] = squared;
  mwi_sum += squared;
  mwi_idx = (mwi_idx + 1) % 30;
  float mwi_val = mwi_sum / 30.0;

  bool beatDetected = false;
  // 550 ms lockout caps physiological resting heart rate limits accurately
  if (mwi_val > signalThreshold && (now - lastRPeakTime) > 550) {
    if (lastRPeakTime > 0) {
      unsigned long rr = now - lastRPeakTime;
      float instBPM = 60000.0 / (float)rr;
      
      if (instBPM >= 45.0 && instBPM <= 120.0) {
        currentBPM = 0.85 * currentBPM + 0.15 * instBPM; // Heavy exponential smoothing
        
        rrIntervals[rrIdx] = rr;
        rrIdx = (rrIdx + 1) % 5;
        float diffSum = 0;
        for (int i = 0; i < 4; i++) {
          float diff = (float)rrIntervals[(i + 1) % 5] - (float)rrIntervals[i];
          diffSum += diff * diff;
        }
        hrvRMSSD = sqrt(diffSum / 4.0);
        beatDetected = true;
      }
    }
    lastRPeakTime = now;
    signalThreshold = 0.70 * signalThreshold + 0.30 * mwi_val;
  } else {
    signalThreshold *= 0.997;
    if (signalThreshold < 1200.0) signalThreshold = 1200.0;
  }

  return beatDetected;
}

void loop() {
  #if defined(STM32F4xx) || defined(STM32F1xx)
  __WFI(); 
  #endif

  if (!sampleReady) return;
  sampleReady = false;

  unsigned long now = millis();

  bool leadsOff = (digitalRead(LO_PLUS_PIN) == HIGH || digitalRead(LO_MINUS_PIN) == HIGH);

  if (leadsOff) {
    currentBPM = 0.0;
    rhythmClass = 2;
    float rawTemp = analogRead(TEMP_PIN);
    float temperatureC = 35.0 + (rawTemp / 4095.0) * 5.0;

    static unsigned long lastLeadOffSend = 0;
    if (now - lastLeadOffSend > 200) { // Limit serial send rate
      lastLeadOffSend = now;
      Serial.print("0.0,0.0,");
      Serial.print(temperatureC, 1);
      Serial.print(",");
      Serial.print(rhythmClass);
      Serial.print(",");
      Serial.println(0.0, 1);
    }
    return;
  }

  float filteredECG = runLevel0_Bandpass(rawECGValue);
  bool possibleBeat = runLevel1_PanTompkins(filteredECG, now);

  static unsigned long lastClassifierRun = 0;
  if (possibleBeat || (now - lastClassifierRun > 250)) {
    lastClassifierRun = now;
    
    float rawTemp = analogRead(TEMP_PIN);
    float temperatureC = 35.0 + (rawTemp / 4095.0) * 5.0;

    rhythmClass = embeddedDecisionTree(currentBPM, temperatureC, hrvRMSSD);

    Serial.print(filteredECG, 1);
    Serial.print(",");
    Serial.print(currentBPM, 1);
    Serial.print(",");
    Serial.print(temperatureC, 1);
    Serial.print(",");
    Serial.print(rhythmClass);
    Serial.print(",");
    Serial.println(hrvRMSSD, 1);
  }
}