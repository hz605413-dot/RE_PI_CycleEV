#(.venv) PS C:\Users\hz605\OneDrive\Desktop\RE_PI_CycleEV> python app.py
#python -c "import tensorflow as tf; print('TensorFlow:', tf.__version__); print('Keras:', tf.keras.__version__)"
import os
import io
import base64
import pickle
import numpy as np
import pandas as pd
import tensorflow as tf

from flask import Flask, render_template, request, jsonify, send_file
import joblib

# ============================================================
# Flask application
# ============================================================


app = Flask(__name__)

# Allow reasonably large CSV uploads
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


# ============================================================
# Paths
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "RE_PI_CycleEV_best_generator.keras"
)

SCALER_PATH = os.path.join(
    BASE_DIR,
    "preprocessing",
    "scaler_minmax.pkl"
)
scaler = joblib.load(SCALER_PATH)


# ============================================================
# Model input/output definitions
# ============================================================

INPUT_COLUMNS = [
    "Battery Current [A]",
    "Battery Temperature [°C]",
    "Velocity [km/h]",
    "Elevation [m]",
    "Throttle [%]",
    "Requested Heating Power [W]",
    "AirCon Power [kW]",
    "Ambient Temperature [°C]",
    "Heating Power CAN [kW]",
    "Heater Signal"
]

OUTPUT_COLUMNS = [
    "SoC [%]",
    "Battery Voltage [V]",
    "Motor Torque [Nm]",
    "Longitudinal Acceleration [m/s^2]"
]

EVENTS = {
    "normal": np.array([0, 0, 0, 0, 0], dtype=np.float32),
    "low_soc": np.array([1, 0, 0, 0, 0], dtype=np.float32),
    "high_current": np.array([0, 1, 0, 0, 0], dtype=np.float32),
    "aggressive": np.array([0, 0, 1, 0, 0], dtype=np.float32),
    "heating": np.array([0, 0, 0, 1, 0], dtype=np.float32),
    "stop_go": np.array([0, 0, 0, 0, 1], dtype=np.float32),
}

EVENT_NAMES = {
    "normal": "Normal",
    "low_soc": "Low SOC",
    "high_current": "High Current",
    "aggressive": "Aggressive Acceleration / Braking",
    "heating": "Heating Stress",
    "stop_go": "Stop-and-Go",
}


# ============================================================
# Load trained model and scaler
# ============================================================

print("Loading RE-PI-CycleEV model...")

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Model not found: {MODEL_PATH}"
    )

if not os.path.exists(SCALER_PATH):
    raise FileNotFoundError(
        f"Scaler not found: {SCALER_PATH}"
    )


# compile=False is sufficient because we only need inference
model = tf.keras.models.load_model(
    MODEL_PATH,
    compile=False
)

print("Model loaded successfully.")
print("Model inputs:", model.input_shape)
print("Model output:", model.output_shape)


# ============================================================
# Helper functions
# ============================================================

def read_uploaded_csv(file):
    """
    Read the uploaded EV CSV file.
    Project CSV files are semicolon-separated and Latin-1 encoded.
    """
    raw = file.read()

    df = pd.read_csv(
        io.BytesIO(raw),
        sep=";",
        encoding="latin1"
    )

    return df

def validate_input_dataframe(df):
    """
    Check whether all required 10 input variables exist.
    """

    missing = [
        col for col in INPUT_COLUMNS
        if col not in df.columns
    ]

    if missing:
        return False, missing

    return True, []


def prepare_input_sequence(df):
    """
    Convert uploaded EV data into one 256 x 10 model input sequence.

    The model was trained using:
        window length = 256
        input features = 10
    """

    if len(df) < 256:
        raise ValueError(
            f"The uploaded file contains only {len(df)} rows. "
            "At least 256 rows are required."
        )

    # Use the first 256 rows
    sequence = df[INPUT_COLUMNS].iloc[:256].copy()

    # Convert to numeric
    for col in INPUT_COLUMNS:
        sequence[col] = pd.to_numeric(
            sequence[col],
            errors="coerce"
        )

    # Check missing/non-numeric values
    if sequence.isnull().any().any():
        bad_columns = sequence.columns[
            sequence.isnull().any()
        ].tolist()

        raise ValueError(
            "Missing or non-numeric values found in: "
            + ", ".join(bad_columns)
        )

    # Convert to numpy
    X_original = sequence.values.astype(np.float32)

    # --------------------------------------------------------
    # The project scaler was fitted on all 14 variables:
    # 10 inputs + 4 outputs.
    #
    # Therefore we create a temporary 14-column array,
    # scale it, and retain the first 10 scaled columns.
    # --------------------------------------------------------

    dummy_14 = np.zeros(
        (256, 14),
        dtype=np.float32
    )

    dummy_14[:, :10] = X_original

    scaled_14 = scaler.transform(dummy_14)

    X_scaled = scaled_14[:, :10]

    # Add batch dimension
    X_scaled = np.expand_dims(
        X_scaled.astype(np.float32),
        axis=0
    )

    return X_original, X_scaled


def inverse_transform_outputs(
    X_original,
    generated_scaled
):
    """
    Convert generated 4-target scaled values back to
    physical units using the original 14-feature scaler.
    """

    generated_scaled = np.asarray(
        generated_scaled,
        dtype=np.float32
    )

    if generated_scaled.ndim == 3:
        generated_scaled = generated_scaled[0]

    # Build a 14-feature scaled array
    combined_scaled = np.zeros(
        (256, 14),
        dtype=np.float32
    )

    # Scale original inputs
    input_scaled = scaler.transform(
        np.concatenate(
            [
                X_original,
                np.zeros((256, 4), dtype=np.float32)
            ],
            axis=1
        )
    )

    combined_scaled[:, :10] = input_scaled[:, :10]
    combined_scaled[:, 10:14] = generated_scaled

    # Inverse transform
    combined_original = scaler.inverse_transform(
        combined_scaled
    )

    generated_original = combined_original[:, 10:14]

    return generated_original


def calculate_statistics(output_array):
    """
    Calculate simple statistics for the generated signals.
    """

    stats = {}

    for i, column in enumerate(OUTPUT_COLUMNS):

        values = output_array[:, i]

        stats[column] = {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
        }

    return stats


# ============================================================
# Routes
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html",
        events=EVENT_NAMES
    )


@app.route("/generate", methods=["POST"])
def generate():

    try:

        # ----------------------------------------------------
        # Check file
        # ----------------------------------------------------

        if "file" not in request.files:

            return jsonify({
                "success": False,
                "error": "No CSV file was uploaded."
            }), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({
                "success": False,
                "error": "Please select a CSV file."
            }), 400

        # ----------------------------------------------------
        # Event condition
        # ----------------------------------------------------

        event_key = request.form.get(
            "event",
            "normal"
        )

        if event_key not in EVENTS:

            return jsonify({
                "success": False,
                "error": "Invalid event condition."
            }), 400

        condition = EVENTS[event_key]

        # ----------------------------------------------------
        # Read CSV
        # ----------------------------------------------------

        df = read_uploaded_csv(file)

        # ----------------------------------------------------
        # Validate columns
        # ----------------------------------------------------

        valid, missing = validate_input_dataframe(df)

        if not valid:

            return jsonify({
                "success": False,
                "error": (
                    "The uploaded CSV is missing required "
                    "columns: "
                    + ", ".join(missing)
                )
            }), 400

        # ----------------------------------------------------
        # Prepare 256 x 10 sequence
        # ----------------------------------------------------

        X_original, X_scaled = prepare_input_sequence(df)

        # ----------------------------------------------------
        # Prepare condition
        # ----------------------------------------------------

        C = np.expand_dims(
            condition,
            axis=0
        )

        # ----------------------------------------------------
        # Generate synthetic targets
        # ----------------------------------------------------

        generated_scaled = model.predict(
            [X_scaled, C],
            verbose=0
        )

        # ----------------------------------------------------
        # Convert back to physical units
        # ----------------------------------------------------

        generated_original = inverse_transform_outputs(
            X_original,
            generated_scaled
        )

        # ----------------------------------------------------
        # Statistics
        # ----------------------------------------------------

        statistics = calculate_statistics(
            generated_original
        )

        # ----------------------------------------------------
        # Prepare chart data
        # ----------------------------------------------------

        chart_data = {}

        for i, column in enumerate(OUTPUT_COLUMNS):

            chart_data[column] = (
                generated_original[:, i]
                .astype(float)
                .tolist()
            )

        # ----------------------------------------------------
        # CSV data for download
        # ----------------------------------------------------

        output_df = pd.DataFrame(
            generated_original,
            columns=OUTPUT_COLUMNS
        )

        csv_buffer = io.StringIO()

        output_df.to_csv(
            csv_buffer,
            index=False
        )

        csv_encoded = base64.b64encode(
            csv_buffer.getvalue().encode("utf-8")
        ).decode("utf-8")

        # ----------------------------------------------------
        # Response
        # ----------------------------------------------------

        return jsonify({

            "success": True,

            "event": EVENT_NAMES[event_key],

            "rows_generated": 256,

            "chart_data": chart_data,

            "statistics": statistics,

            "csv": csv_encoded,

            "output_columns": OUTPUT_COLUMNS

        })

    except Exception as e:

        print("ERROR:", str(e))

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# ============================================================
# Health check
# ============================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "model_loaded": True
    })


# ============================================================
# Run application
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )