# RE-PI-CycleEV Web Application

## Rare-Event-Aware Physics-Informed Conditional GAN for Multivariate Electric-Vehicle Time-Series Synthesis

This project provides a web interface for the trained RE-PI-CycleEV generator.

The original research project develops a conditional generative model for synthetic electric-vehicle time-series generation. The web application provides a simple interface for using the trained generator.

---

## Project Purpose

The application accepts a 256-row EV input sequence containing 10 input variables and a selected event condition.

The trained RE-PI-CycleEV generator produces four target time-series signals:

1. State of Charge (SoC)
2. Battery Voltage
3. Motor Torque
4. Longitudinal Acceleration

---

## Model

The deployed model is the trained RE-PI-CycleEV generator.

The model uses:

- 10 EV input variables
- 5 event-condition variables
- 256 time steps
- 4 generated target variables

---

## Input Variables

The uploaded CSV must contain the following columns:

- Battery Current [A]
- Battery Temperature [°C]
- Velocity [km/h]
- Elevation [m]
- Throttle [%]
- Requested Heating Power [W]
- AirCon Power [kW]
- Ambient Temperature [°C]
- Heating Power CAN [kW]
- Heater Signal

At least 256 rows are required.

The application uses the first 256 valid rows.

---

## Event Conditions

The application supports:

- Normal
- Low SOC
- High Current
- Aggressive Acceleration / Braking
- Heating Stress
- Stop-and-Go

The selected condition is passed to the conditional generator.

---

## Generated Outputs

The model generates:

- SoC [%]
- Battery Voltage [V]
- Motor Torque [Nm]
- Longitudinal Acceleration [m/s²]

The generated values are converted back from normalized model space to physical units using the project's trained scaler.

---

## Project Structure

```text
RE_PI_CycleEV/
│
├── app.py
├── requirements.txt
├── Procfile
├── README.md
│
├── models/
│   └── RE_PI_CycleEV_best_generator.keras
│
├── preprocessing/
│   └── scaler_minmax.pkl
│
├── templates/
│   └── index.html
│
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── script.js