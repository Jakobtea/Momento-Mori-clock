document.addEventListener('DOMContentLoaded', () => {
    const birthdateInput = document.getElementById('birthdate');
    const genderInputs = document.querySelectorAll('input[name="gender"]');
    const smokerCheckbox = document.getElementById('smoker');
    const obeseCheckbox = document.getElementById('obese');
    const exerciseCheckbox = document.getElementById('exercise');
    const healthyDietCheckbox = document.getElementById('healthy-diet');
    const startClockButton = document.getElementById('start-clock');
    const inputSection = document.getElementById('input-section');
    const clockSection = document.getElementById('clock-section');
    const countdownDisplay = document.getElementById('countdown-display');
    const mementoQuote = document.getElementById('memento-quote');
    const endMessage = document.getElementById('end-message');

    let countdownInterval;
    let targetEndDate;

    // Latin quotes for memento mori
    const quotes = [
        "Memento Mori",
        "Carpe Diem",
        "Ars longa, vita brevis",
        "Pulvis et umbra sumus",
        "Vivere est cogitare",
        "Tempus Fugit'"
    ];

    // Function to set a random quote
    const setRandomQuote = () => {
        const randomIndex = Math.floor(Math.random() * quotes.length);
        mementoQuote.innerHTML = quotes[randomIndex]; // Use innerHTML for bolding
    };

    // Initialize with a random quote
    setRandomQuote();

    /**
     * Calculates an estimated lifespan in years based on user inputs.
     * This is a simplified model for illustrative purposes only and is not medical advice.
     * Consult a healthcare professional for personalized health information.
     * @returns {number} Estimated lifespan in years.
     */
    const calculateEstimatedLifespan = () => {
        let estimatedYears = 75; // Base lifespan in years (e.g., global average)

        // Gender adjustment
        const selectedGender = document.querySelector('input[name="gender"]:checked').value;
        if (selectedGender === 'female') {
            estimatedYears += 5; // Women generally have a higher life expectancy
        } else {
            // Male or other, no specific adjustment from base
        }

        // Lifestyle adjustments
        if (smokerCheckbox.checked) {
            estimatedYears -= 10; // Smoking significantly reduces lifespan
        }
        if (obeseCheckbox.checked) {
            estimatedYears -= 5; // Obesity can reduce lifespan
        }
        if (exerciseCheckbox.checked) {
            estimatedYears += 3; // Regular exercise can increase lifespan
        }
        if (healthyDietCheckbox.checked) {
            estimatedYears += 2; // Healthy diet can increase lifespan
        }

        // Ensure a reasonable minimum lifespan
        return Math.max(1, estimatedYears);
    };

    // Function to update the countdown display
    const updateCountdownDisplay = (seconds) => {
        if (seconds < 0) {
            countdownDisplay.textContent = '0'; // Display 0 when time is up
            endMessage.textContent = "Time has elapsed. Live on through your legacy.";
            clearInterval(countdownInterval);
            return;
        }
        countdownDisplay.textContent = seconds.toString();
    };

    startClockButton.addEventListener('click', () => {
        const birthdate = new Date(birthdateInput.value);

        if (!birthdateInput.value) {
            // Using a simple alert for now, as custom modals are more complex
            // For a production app, you'd replace this with a styled message box.
            alert('Please enter your birthdate.');
            return;
        }

        const estimatedLifespanYears = calculateEstimatedLifespan();

        // Calculate the estimated end date
        const birthYear = birthdate.getFullYear();
        const birthMonth = birthdate.getMonth();
        const birthDay = birthdate.getDate();

        // Create a new Date object for the estimated end date
        // Note: Adding years directly to a Date object can sometimes have issues with leap years/month ends.
        // A safer way is to add milliseconds, but for simplicity, this works for years.
        targetEndDate = new Date(birthYear + estimatedLifespanYears, birthMonth, birthDay);

        // Hide input, show clock
        inputSection.classList.add('hidden');
        clockSection.classList.remove('hidden');

        // Start the countdown
        clearInterval(countdownInterval); // Clear any existing interval
        countdownInterval = setInterval(() => {
            const now = new Date();
            const remainingTimeMs = targetEndDate.getTime() - now.getTime();
            const remainingSeconds = Math.max(0, Math.floor(remainingTimeMs / 1000)); // Ensure it doesn't go negative before 0

            updateCountdownDisplay(remainingSeconds);

            if (remainingSeconds <= 0) {
                clearInterval(countdownInterval);
                endMessage.textContent = "Time has elapsed. Live on through your legacy.";
            }
        }, 1000); // Update every second
    });

    // Optional: Pre-fill birthdate with a reasonable default or clear it
    // birthdateInput.valueAsDate = new Date(); // Sets today's date
});