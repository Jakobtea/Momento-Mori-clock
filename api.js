// --- api.js: Configuration and Core API Calls ---

const API_KEY_PLACEHOLDER = "YOUR_GEMINI_API_KEY_HERE"; // !!! REPLACE THIS !!!
const API_URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models";
const MODEL = "gemini-2.5-flash-preview-05-20"; 
const API_URL = `${API_URL_BASE}/${MODEL}:generateContent?key=${API_KEY_PLACEHOLDER}`;

/**
 * Common check for API key presence.
 */
function checkApiKey() {
    if (API_KEY_PLACEHOLDER.includes("YOUR_GEMINI_API_KEY_HERE")) {
        console.error("API Key is missing. Please replace YOUR_GEMINI_API_KEY_HERE.");
        return false;
    }
    return true;
}

/**
 * Calls the Gemini API requesting a structured JSON response.
 * @param {string} userText - The user's input text.
 * @param {string} systemInstruction - The system persona/instruction.
 * @param {object} responseSchema - The JSON schema for the output.
 * @returns {Promise<object|null>} The parsed JSON object or null on failure.
 */
async function callGeminiApiStructured(userText, systemInstruction, responseSchema) {
    if (!checkApiKey()) return null;

    const payload = {
        contents: [{ parts: [{ text: userText }] }],
        systemInstruction: { parts: [{ text: systemInstruction }] },
        generationConfig: {
            responseMimeType: "application/json",
            responseSchema: responseSchema
        }
    };

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error(`API call failed: ${response.status} ${response.statusText}`);
        
        const jsonResponse = await response.json();
        const jsonText = jsonResponse?.candidates?.[0]?.content?.parts?.[0]?.text;
        
        return jsonText ? JSON.parse(jsonText) : null;
    } catch (error) {
        console.error("Gemini API Structured Error:", error);
        throw new Error("API call failed (Structured).");
    }
}

/**
 * Calls the Gemini API requesting a plain text response, often used for chat history.
 * @param {Array<object>} contentsList - The conversation history/prompt in API format.
 * @param {string} systemInstruction - The system persona/instruction.
 * @returns {Promise<string|null>} The generated text response or null on failure.
 */
async function callGeminiApiPlain(contentsList, systemInstruction) {
    if (!checkApiKey()) return null;

    const payload = {
        contents: contentsList,
        systemInstruction: { parts: [{ text: systemInstruction }] },
    };

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error(`API call failed: ${response.status} ${response.statusText}`);

        const jsonResponse = await response.json();
        return jsonResponse?.candidates?.[0]?.content?.parts?.[0]?.text || "Failed to generate response.";

    } catch (error) {
        console.error("Gemini API Plain Text Error:", error);
        throw new Error("API call failed (Plain Text).");
    }
}