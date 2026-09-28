// =========================================================
// Global chart objects
// =========================================================

let charts = {};

let generatedCSV = null;


// =========================================================
// Form
// =========================================================

const form =
    document.getElementById(
        "generationForm"
    );

const button =
    document.getElementById(
        "generateButton"
    );

const statusBox =
    document.getElementById(
        "status"
    );

const resultsSection =
    document.getElementById(
        "resultsSection"
    );


// =========================================================
// Status message
// =========================================================

function showStatus(
    message,
    isError = false
) {

    statusBox.textContent = message;

    statusBox.classList.remove(
        "hidden"
    );

    statusBox.classList.toggle(
        "error",
        isError
    );
}


function hideStatus() {

    statusBox.classList.add(
        "hidden"
    );

}


// =========================================================
// Create Chart
// =========================================================

function createChart(
    canvasId,
    label,
    values,
    yTitle
) {

    // Destroy previous chart
    if (charts[canvasId]) {

        charts[canvasId].destroy();

    }


    const ctx =
        document
            .getElementById(canvasId)
            .getContext("2d");


    const labels =
        values.map(
            (_, index) => index
        );


    charts[canvasId] =
        new Chart(
            ctx,
            {

                type: "line",

                data: {

                    labels: labels,

                    datasets: [
                        {

                            label: label,

                            data: values,

                            borderWidth: 2,

                            pointRadius: 0,

                            tension: 0.15

                        }
                    ]

                },

                options: {

                    responsive: true,

                    interaction: {

                        intersect: false,

                        mode: "index"

                    },

                    plugins: {

                        legend: {

                            display: true

                        }

                    },

                    scales: {

                        x: {

                            title: {

                                display: true,

                                text:
                                    "Time Step"

                            }

                        },

                        y: {

                            title: {

                                display: true,

                                text:
                                    yTitle

                            }

                        }

                    }

                }

            }
        );

}


// =========================================================
// Statistics
// =========================================================

function displayStatistics(
    statistics
) {

    const container =
        document.getElementById(
            "statistics"
        );


    container.innerHTML = "";


    Object.entries(
        statistics
    ).forEach(
        ([name, values]) => {

            const card =
                document.createElement(
                    "div"
                );

            card.className =
                "stat-card";


            card.innerHTML = `

                <h3>
                    ${name}
                </h3>

                <div class="stat-row">
                    <span>Mean</span>
                    <strong>
                        ${values.mean.toFixed(4)}
                    </strong>
                </div>

                <div class="stat-row">
                    <span>Std</span>
                    <strong>
                        ${values.std.toFixed(4)}
                    </strong>
                </div>

                <div class="stat-row">
                    <span>Minimum</span>
                    <strong>
                        ${values.min.toFixed(4)}
                    </strong>
                </div>

                <div class="stat-row">
                    <span>Maximum</span>
                    <strong>
                        ${values.max.toFixed(4)}
                    </strong>
                </div>

            `;


            container.appendChild(
                card
            );

        }
    );

}


// =========================================================
// Form submission
// =========================================================

form.addEventListener(
    "submit",
    async function (event) {

        event.preventDefault();


        const fileInput =
            document.getElementById(
                "csvFile"
            );

        const eventInput =
            document.getElementById(
                "event"
            );


        if (
            !fileInput.files ||
            fileInput.files.length === 0
        ) {

            showStatus(
                "Please select a CSV file.",
                true
            );

            return;

        }


        const file =
            fileInput.files[0];


        // Basic extension check

        if (
            !file.name
                .toLowerCase()
                .endsWith(".csv")
        ) {

            showStatus(
                "Please upload a CSV file.",
                true
            );

            return;

        }


        // -------------------------------------------------
        // Prepare form data
        // -------------------------------------------------

        const formData =
            new FormData();

        formData.append(
            "file",
            file
        );

        formData.append(
            "event",
            eventInput.value
        );


        // -------------------------------------------------
        // Loading state
        // -------------------------------------------------

        button.disabled = true;

        button.textContent =
            "Generating...";


        showStatus(
            "Loading the EV sequence and generating synthetic data..."
        );


        try {

            const response =
                await fetch(
                    "/generate",
                    {

                        method: "POST",

                        body: formData

                    }
                );


            const data =
                await response.json();


            if (
                !response.ok ||
                !data.success
            ) {

                throw new Error(
                    data.error ||
                    "Generation failed."
                );

            }


            // -------------------------------------------------
            // Store CSV
            // -------------------------------------------------

            generatedCSV =
                data.csv;


            // -------------------------------------------------
            // Display summary
            // -------------------------------------------------

            document.getElementById(
                "selectedEvent"
            ).textContent =
                data.event;


            document.getElementById(
                "rowsGenerated"
            ).textContent =
                data.rows_generated;


            // -------------------------------------------------
            // Display charts
            // -------------------------------------------------

            createChart(
                "socChart",
                "SoC",
                data.chart_data[
                    "SoC [%]"
                ],
                "SoC (%)"
            );


            createChart(
                "voltageChart",
                "Battery Voltage",
                data.chart_data[
                    "Battery Voltage [V]"
                ],
                "Voltage (V)"
            );


            createChart(
                "torqueChart",
                "Motor Torque",
                data.chart_data[
                    "Motor Torque [Nm]"
                ],
                "Torque (Nm)"
            );


            createChart(
                "accelerationChart",
                "Longitudinal Acceleration",
                data.chart_data[
                    "Longitudinal Acceleration [m/s^2]"
                ],
                "Acceleration (m/s²)"
            );


            // -------------------------------------------------
            // Statistics
            // -------------------------------------------------

            displayStatistics(
                data.statistics
            );


            // -------------------------------------------------
            // Show results
            // -------------------------------------------------

            resultsSection.classList.remove(
                "hidden"
            );


            showStatus(
                "Synthetic EV time-series generated successfully."
            );


            // Scroll to results

            resultsSection.scrollIntoView({
                behavior: "smooth"
            });


        } catch (error) {

            console.error(
                error
            );


            showStatus(
                error.message ||
                "An unexpected error occurred.",
                true
            );

        } finally {

            button.disabled = false;

            button.textContent =
                "Generate Synthetic Data";

        }

    }
);


// =========================================================
// Download generated CSV
// =========================================================

document
    .getElementById(
        "downloadButton"
    )
    .addEventListener(
        "click",
        function () {

            if (!generatedCSV) {

                alert(
                    "Generate data first."
                );

                return;

            }


            const binary =
                atob(
                    generatedCSV
                );


            const bytes =
                new Uint8Array(
                    binary.length
                );


            for (
                let i = 0;
                i < binary.length;
                i++
            ) {

                bytes[i] =
                    binary.charCodeAt(i);

            }


            const blob =
                new Blob(
                    [bytes],
                    {
                        type:
                            "text/csv;charset=utf-8;"
                    }
                );


            const url =
                URL.createObjectURL(
                    blob
                );


            const link =
                document.createElement(
                    "a"
                );


            link.href =
                url;


            link.download =
                "RE_PI_CycleEV_generated.csv";


            document
                .body
                .appendChild(link);


            link.click();


            link.remove();


            URL.revokeObjectURL(
                url
            );

        }
    );