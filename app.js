// --- app.js: Main Application Logic and UI Management ---

const thoughtExplorer = (function() {
    // --- System Instructions and JSON Schema ---
    const RESPONSE_SCHEMA = {
        type: "OBJECT",
        properties: {
            corrected_text: { type: "STRING" },
            challenge_questions: { type: "ARRAY", items: { type: "STRING" } }
        },
        required: ["corrected_text", "challenge_questions"]
    };

    // NEW CONSTANT for Local Storage Key
    const SESSIONS_STORAGE_KEY = 'thoughtExplorerSessions';

    const THOUGHT_COACH_SYSTEM_INSTRUCTION = (
        "You are a world-class language tutor and deep-thinking coach, similar to Ali Abdall's Voicepal. "
        + "Your primary task is two-fold. First, take the raw, error-prone user transcription, correct all grammatical errors, smooth out "
        + "pauses, filler words, and repetitions, and output it as clear, coherent, formal English text. "
        + "Second, based *only* on the refined text, generate precisely 3 unique, thought-provoking questions. "
        + "These questions must challenge the core assumption, explore the central idea's consequences, or push "
        + "the user to consider the opposite perspective."
    );

    const BLOG_SYSTEM_INSTRUCTION = (
        "You are a skilled content creator. Take the provided thought process, which is a sequence of initial thought and responses to challenge questions. "
        + "Write a concise, engaging, and reflective blog post (3-4 paragraphs) that summarizes the core idea and the journey of exploration the user took. "
        + "Use a positive and encouraging tone, suitable for a young audience, avoiding complex jargon."
        + "Format the output as clear, clean text."
    );
    
    // --- Debate Opponent Personas and Instructions (Revised) ---
    const DEBATE_OPPONENTS = {
        martin: {
            name: "Martin (The Emotional Everyman)",
            description: "The weakest opponent. Emotional, uses normal, everyday speech, and can be easily thrown off. A random person on the street.",
            instruction: (
                "You are 'Martin', a weak, emotional debater. Your speech is casual and everyday, and your arguments often rely on anecdote or simple feelings rather than logic. "
                + "Analyze the user's previous statement and give a simple, often emotional or poorly structured, counter-argument. You are not a rigorous academic. "
                + "Do not use complex vocabulary. Respond in plain text only. Always end by asking a question that prompts the user's next point."
            )
        },
        goodie: {
            name: "Goodie (The Logical Professional)",
            description: "A smart, logical professional with workplace debating experience. She's strong but can be emotional and is not used to competitive debating.",
            instruction: (
                "You are 'Goodie', a smart, logical debater with professional experience. Your arguments are well-reasoned and grounded in practical, real-world logic, but you can sometimes let emotion creep in or become too focused on one detail. "
                + "Analyze the user's statement and deliver a concise, logical rebuttal, occasionally showing frustration or personal investment. "
                + "Keep your response focused and always end by prompting the user for their next point. Respond in plain text only."
            )
        },
        ishikawa: {
            name: "Ishikawa (The Rhetorical Master)",
            description: "The strongest opponent. He uses excellent language, rhetoric, and logical fallacies to trip up the opponent.",
            instruction: (
                "You are 'Ishikawa', a highly skilled, intellectual, and competitive debater. Your responses are characterized by excellent, precise language, complex arguments, and a heavy use of **rhetorical devices** (like *ad hominem*, *straw man*, *false dichotomy*) and subtle **logical fallacies** to make the opponent 'trip up' or lose footing. "
                + "Analyze the user's statement and generate a sophisticated, challenging counter-argument, focusing on elegant phrasing and psychological pressure. "
                + "Keep your response focused and always end by prompting the user for their next point. Respond in plain text only."
            )
        }
    };
    
    const SUMMARIZE_DEBATE_SYSTEM_INSTRUCTION = (
        "You are an impartial analyst. Take the provided debate transcript, which is a sequence of arguments and rebuttals between a user and an AI devil's advocate. "
        + "Write a concise, objective summary (3-4 paragraphs) of the core contention, the main arguments from each side, and the overall trajectory of the discussion. "
        + "The summary should be formatted as clean, clear text. Do not take a side."
        + "Use a neutral, academic tone suitable for a general audience."
        + "Finish by stating a clear opinion on who presented the stronger case and why. and what could be improved by each side."
    );


    // --- DOM Elements ---
    const logContainer = document.getElementById('log-container');
    const questionsContainer = document.getElementById('questions-container');
    const selectedQuestionLabel = document.getElementById('selected-question-label');
    const guidedActions = document.getElementById('guided-actions');
    const debateActions = document.getElementById('debate-actions');
    const inputText = document.getElementById('input-text');
    const processButton = document.getElementById('process-button');
    const debateStartButton = document.getElementById('debate-start-button');
    const confirmButton = document.getElementById('confirm-button');
    const blogButton = document.getElementById('blog-button');
    const summarizeDebateButton = document.getElementById('summarize-debate-button');
    const endDebateButton = document.getElementById('end-debate-button');
    const statusLabel = document.getElementById('status-label');
    const modal = document.getElementById('modal');
    const modalContent = document.getElementById('modal-content');
    const modalTitle = document.getElementById('modal-title');
    const themeToggleButton = document.getElementById('theme-toggle-button');
    
    // SESSION DOM ELEMENTS
    const sidebar = document.getElementById('session-sidebar'); 
    const newChatButton = document.getElementById('new-chat-button');
    const titleHeader = document.getElementById('title-header');


    // --- State Variables ---
    let loadingActive = false;
    let loadingInterval = null;
    let selectedQuestion = null; 
    let currentStepData = null; 
    let conversationHistory = []; 
    let currentStep = 1; 
    let isDebating = false;
    let debateHistory = []; 
    let selectedOpponentKey = null; 
    
    // SESSION STATE VARIABLES
    let allSessions = [];       
    let currentSessionId = null; 
    let currentSessionType = 'guided'; 
    let sessionTitle = 'New Session';
    
    
    // --- Theme Toggling Logic ---
    function applyTheme(isLight) {
        const body = document.body;
        if (isLight) {
            body.classList.add('light-theme');
            themeToggleButton.textContent = "Dark Mode";
            window.localStorage.setItem('theme', 'light');
        } else {
            body.classList.remove('light-theme');
            themeToggleButton.textContent = "Light Mode";
            window.localStorage.setItem('theme', 'dark');
        }
    }

    function toggleTheme() {
        const isLight = document.body.classList.contains('light-theme');
        applyTheme(!isLight);
    }

    function initializeTheme() {
        const savedTheme = window.localStorage.getItem('theme');
        if (savedTheme === 'light') {
            applyTheme(true);
        } else {
            applyTheme(false); 
        }
    }
    
    
    // --- Session Management (Persistence) ---

    function loadAllSessions() {
        try {
            const sessionsData = window.localStorage.getItem(SESSIONS_STORAGE_KEY);
            allSessions = sessionsData ? JSON.parse(sessionsData) : [];
            renderSidebar();
        } catch (error) {
            console.error("Error loading sessions from localStorage:", error);
            allSessions = [];
        }
    }

    function saveCurrentSession() {
        if (!conversationHistory.length && debateHistory.length <= 1) return; // Don't save empty sessions

        const now = new Date().toISOString();
        const currentSession = {
            id: currentSessionId || (window.crypto && window.crypto.randomUUID ? window.crypto.randomUUID() : Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)),
            title: sessionTitle || (currentSessionType === 'guided' ? 'Guided Thought' : 'Debate'),
            type: currentSessionType,
            date: now,
            guided: conversationHistory,
            debate: debateHistory,
            opponent: selectedOpponentKey
        };
        
        // Update session in array or add new one
        const index = allSessions.findIndex(s => s.id === currentSession.id);
        if (index > -1) {
            allSessions[index] = currentSession; // Update existing
        } else {
            allSessions.unshift(currentSession); // Add new to the top
        }
        
        // Update state and persistence
        currentSessionId = currentSession.id; 
        window.localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(allSessions));
        renderSidebar();
    }
    
    function loadSession(id) {
        const session = allSessions.find(s => s.id === id);
        if (!session) return;
        
        // 1. Reset the UI/state (Clears log, but keeps sidebar state)
        resetApp(true, false); 

        // 2. Load the state
        currentSessionId = session.id;
        sessionTitle = session.title;
        currentSessionType = session.type;
        currentStep = session.guided ? session.guided.length + 1 : 1;


        if (session.type === 'guided') {
            isDebating = false;
            conversationHistory = session.guided || [];
            
            // Reconstruct conversation flow in the log
            logContainer.innerHTML = '';
            conversationHistory.forEach(item => {
                appendToLog('USER', item.thought, 'user');
                appendToLog('AI', `Focus on: "${item.focus_question}"`, 'ai');
            });
            
            stopLoadingAnimation(`Loaded Guided Session: Step ${currentStep}.`, 'var(--color-accent-orange)');
            guidedActions.style.display = 'flex'; 
            debateStartButton.style.display = 'inline-block';
            
        } else if (session.type === 'debate') {
            isDebating = true;
            debateHistory = session.debate || [];
            selectedOpponentKey = session.opponent;
            
            // Reconstruct debate flow in the log
            logContainer.innerHTML = '';
            debateHistory.forEach(entry => {
                const tag = entry.role === 'user' ? 'user' : 'debate';
                appendToLog(entry.role, entry.parts[0].text, tag);
            });
            
            // Switch UI to debate mode
            questionsContainer.style.display = 'none';
            selectedQuestionLabel.style.display = 'none';
            guidedActions.style.display = 'none';
            debateActions.style.display = 'flex';
            debateStartButton.style.display = 'none';
            processButton.textContent = "Send Rebuttal";
            processButton.classList.remove('process-btn');
            processButton.classList.add('accent-btn');

            stopLoadingAnimation(`Loaded Debate against ${DEBATE_OPPONENTS[selectedOpponentKey].name.split(' ')[0]}. Enter your next rebuttal.`, 'var(--color-accent-orange)');
        }
        
        // 3. Update UI header and highlight sidebar item
        titleHeader.textContent = sessionTitle;
        document.querySelectorAll('.session-item').forEach(item => {
            item.classList.toggle('active', item.dataset.id === id);
        });
    }

    /** NEW FUNCTION: Deletes a session and updates the UI/state. */
    function deleteSession(id) {
        // Confirmation dialog for safety
        if (!window.confirm("Are you sure you want to delete this session? This action cannot be undone.")) {
            return;
        }

        // 1. Filter out the deleted session
        allSessions = allSessions.filter(s => s.id !== id);
        
        // 2. Update localStorage
        window.localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(allSessions));
        
        // 3. If the deleted session was the active one, reset the app state
        if (id === currentSessionId) {
            resetApp(true, true);
            stopLoadingAnimation("Session deleted. Ready to start a new session.", 'var(--color-alert)');
        }
        
        // 4. Re-render the sidebar
        renderSidebar();
    }

    // --- UI Rendering ---
    
    /** NEW FUNCTION: Handles the click on the sidebar to distinguish between loading and deleting. */
    function handleSidebarClick(event) {
        const target = event.target;
        
        // 1. Check if the target is the delete button or its icon
        if (target.classList.contains('delete-session-btn') || target.closest('.delete-session-btn')) {
            const button = target.closest('.delete-session-btn');
            const sessionId = button.dataset.id;
            deleteSession(sessionId);
            event.stopPropagation(); // Prevent the parent session item click (load)
            return;
        }

        // 2. If it's a session item, load it
        const sessionItem = target.closest('.session-item');
        if (sessionItem) {
            loadSession(sessionItem.dataset.id);
        }
    }
    
    function renderSidebar() {
        const sidebarContent = sidebar; 
        sidebarContent.innerHTML = ''; // Clear existing items

        if (allSessions.length === 0) {
            const p = document.createElement('p');
            p.classList.add('sidebar-empty');
            p.textContent = 'No saved sessions yet. Start a new chat!';
            sidebarContent.appendChild(p);
            return;
        }

        allSessions.forEach(session => {
            const item = document.createElement('div');
            item.classList.add('session-item');
            if (session.id === currentSessionId) {
                item.classList.add('active');
            }
            item.dataset.id = session.id;
            
            const dateStr = new Date(session.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            const opponentKey = session.opponent || 'guided';
            
            let sessionTypeIcon = '💡'; // Default guided
            if (session.type === 'debate') {
                sessionTypeIcon = opponentKey === 'martin' ? '🫂' : (opponentKey === 'goodie' ? '💼' : '👑');
            }
            
            item.innerHTML = `
                <div class="session-info">
                    <span class="session-icon">${sessionTypeIcon}</span>
                    <span class="session-title">${session.title.substring(0, 30)}</span>
                </div>
                <span class="session-date">${dateStr}</span>
                <button class="delete-session-btn" data-id="${session.id}">
                    <span class="delete-icon">✕</span>
                </button>
            `;
            
            // Note: Click listener is now handled by the parent 'sidebar' container via delegation
            sidebarContent.appendChild(item);
        });
        
        // Ensure the delegated listener is active (it will be added in the init block)
    }


    // --- Utility Functions ---

    /** Appends a message to the conversation log. */
    function appendToLog(sender, text, tag) {
        const entry = document.createElement('div');
        entry.classList.add('log-entry', tag);
        
        const formattedText = text.replace(/\n/g, '<br>');

        if (tag === 'user' || tag === 'ai' || tag === 'debate') {
            const label = document.createElement('span');
            label.classList.add('label');
            if (tag === 'user') label.textContent = "YOU (Refined):";
            if (tag === 'ai') label.textContent = "AI Coach:";
            
            if (tag === 'debate') {
                const opponentName = selectedOpponentKey ? DEBATE_OPPONENTS[selectedOpponentKey].name.split(' ')[0].toUpperCase() : 'AI OPPONENT';
                label.textContent = `${opponentName}:`;
            }
            entry.appendChild(label);
            entry.innerHTML += formattedText;
        } else {
            entry.innerHTML = formattedText;
        }

        logContainer.appendChild(entry);
        logContainer.scrollTop = logContainer.scrollHeight; // Scroll to bottom
    }

    /** Enables/Disables all relevant control buttons in the current mode. */
    function setButtonsState(isDisabled) {
        if (isDebating) {
            processButton.disabled = isDisabled; 
            summarizeDebateButton.disabled = isDisabled;
            endDebateButton.disabled = isDisabled;
        } else { // Guided Mode
            processButton.disabled = isDisabled;
            debateStartButton.disabled = isDisabled; 
            confirmButton.disabled = isDisabled;
            blogButton.disabled = isDisabled;
        }
        
        if (!isDebating) {
            debateStartButton.disabled = isDisabled;
        }
        themeToggleButton.disabled = isDisabled;
        newChatButton.disabled = isDisabled;
    }

    function startLoadingAnimation(message = "AI is thinking") {
        loadingActive = true;
        setButtonsState(true);
        statusLabel.classList.add('loading-animation-active'); 
        
        let state = 0;

        function animate() {
            if (!loadingActive) return;
            const dots = ".".repeat(state % 4);
            statusLabel.textContent = message + dots;
            statusLabel.style.color = 'var(--color-accent-orange)';
            state++;
        }

        clearInterval(loadingInterval);
        loadingInterval = setInterval(animate, 300);
    }

    function stopLoadingAnimation(finalText, finalColor = 'var(--color-text-low)') {
        loadingActive = false;
        clearInterval(loadingInterval);
        statusLabel.textContent = finalText;
        statusLabel.style.color = finalColor;
        statusLabel.classList.remove('loading-animation-active'); 
        
        if (isDebating) {
            processButton.textContent = "Send Rebuttal";
            processButton.classList.remove('process-btn');
            processButton.classList.add('accent-btn');
            summarizeDebateButton.disabled = (debateHistory.length <= 1);
        } else {
            processButton.textContent = "Process Thought";
            processButton.classList.remove('accent-btn');
            processButton.classList.add('process-btn');
        }
        setButtonsState(false);
    }

    function showModal(title, content) {
        modalTitle.textContent = title;
        
        let htmlContent = content.split('\n\n').map(p => {
            if (p.startsWith('* ') || p.startsWith('- ')) {
                const items = p.split('\n').map(item => `<li>${item.replace(/[*-\s]*/, '').trim()}</li>`).join('');
                return `<ul>${items}</ul>`;
            }
            return `<p>${p.replace(/\n/g, '<br>')}</p>`;
        }).join('');

        modalContent.innerHTML = htmlContent;
        modal.style.display = 'flex';
    }
    
    function closeModal(event) {
        if (event.target.classList.contains('modal-overlay')) {
            modal.style.display = 'none';
            
            if (!isDebating && !currentSessionId && currentSessionType === 'debate') {
                selectedOpponentKey = null;
                currentSessionType = 'guided'; 
                titleHeader.textContent = 'New Session';
            }
            setButtonsState(false);
        }
    }
    
    function showOpponentSelectionModal(claim) {
        modalTitle.textContent = "Select Your Debate Opponent";
        
        let contentHTML = `
            <p>You are about to debate the claim: <strong>"${claim}"</strong></p>
            <p>Please choose your opponent. Each has a distinct style and skill level:</p>
            <div id="opponent-cards-container">
        `;

        for (const key in DEBATE_OPPONENTS) {
            const opponent = DEBATE_OPPONENTS[key];
            contentHTML += `
                <div class="opponent-card" data-opponent-key="${key}">
                    <h3>${opponent.name}</h3>
                    <p>${opponent.description}</p>
                    <button class="select-opponent-btn accent-btn" data-key="${key}">Select ${opponent.name.split(' ')[0]}</button>
                </div>
            `;
        }
        
        contentHTML += `</div>`;
        modalContent.innerHTML = contentHTML;
        modal.style.display = 'flex';
        
        document.querySelectorAll('.select-opponent-btn').forEach(button => {
            button.onclick = (e) => {
                const key = e.target.dataset.key;
                selectOpponent(key, claim); 
            };
        });
        
        setButtonsState(true);
    }
    
    async function selectOpponent(key, claim) {
        selectedOpponentKey = key;
        modal.style.display = 'none';
        
        isDebating = true;
        debateHistory = [{ role: "user", parts: [{ text: claim }] }];
        
        questionsContainer.style.display = 'none';
        selectedQuestionLabel.style.display = 'none';
        guidedActions.style.display = 'none';
        debateActions.style.display = 'flex';
        
        processButton.textContent = "Send Rebuttal";
        processButton.classList.remove('process-btn');
        processButton.classList.add('accent-btn');
        debateStartButton.style.display = 'none';

        appendToLog('SYSTEM', `Debate Mode Started against **${DEBATE_OPPONENTS[key].name}**!`, 'system');
        appendToLog('USER', claim, 'user');
        
        saveCurrentSession();
        
        await getAiRebuttal();
    }


    // --- Guided Mode Methods ---

    async function processInput() {
        if (isDebating) {
            sendDebateRebuttal();
            return;
        }
        
        const rawText = inputText.value.trim();
        if (!rawText) {
            alert("Please enter a thought to process.");
            return;
        }
        
        if (currentStep === 1 && !currentSessionId) {
            currentSessionType = 'guided';
            sessionTitle = rawText.substring(0, 40) + (rawText.length > 40 ? '...' : '');
            titleHeader.textContent = sessionTitle;
        }
        
        setButtonsState(true);
        startLoadingAnimation("Analyzing and refining thought...");

        try {
            // CALL FROM API.JS (Requires window.callGeminiApiStructured to be defined)
            const result = await window.callGeminiApiStructured(rawText, THOUGHT_COACH_SYSTEM_INSTRUCTION, RESPONSE_SCHEMA);
            
            if (result && result.corrected_text) {
                currentStepData = result;
                
                appendToLog('USER', result.corrected_text, 'user');
                createQuestionCards(result.challenge_questions);
                
                stopLoadingAnimation(`Thought analyzed. Step ${currentStep}: Select a question to focus your next thought.`, 'var(--color-accent-orange)');
                
                setButtonsState(false);
                confirmButton.disabled = true; 
                
                saveCurrentSession(); 
                
            } else {
                stopLoadingAnimation("Analysis failed. Please try again or check your API key.", 'var(--color-alert)');
                setButtonsState(false);
            }

        } catch (error) {
            stopLoadingAnimation("An API error occurred. See console for details.", 'var(--color-alert)');
            setButtonsState(false);
            console.error("API Error:", error);
            alert("API Error: " + error.message);
        }
    }
    
    function createQuestionCards(questions) {
        questionsContainer.style.display = 'grid'; 
        selectedQuestionLabel.style.display = 'block';
        guidedActions.style.display = 'flex';
        debateActions.style.display = 'none';

        questionsContainer.innerHTML = '';
        selectedQuestion = null;
        selectedQuestionLabel.textContent = "Select one of the challenge questions below to focus your next response.";
        selectedQuestionLabel.style.color = 'var(--color-text-low)'; 
        
        questions.forEach((q) => {
            const card = document.createElement('div');
            card.classList.add('question-card');
            card.innerHTML = `<span class="text">${q}</span>`;
            card.onclick = () => selectQuestion(q, card);
            questionsContainer.appendChild(card);
        });
    }

    function selectQuestion(questionText, currentCard) {
        document.querySelectorAll('.question-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        currentCard.classList.add('selected');
        selectedQuestion = questionText; 
        selectedQuestionLabel.textContent = `Selected Focus: ${questionText}`;
        selectedQuestionLabel.style.color = 'var(--color-accent-orange)';
        confirmButton.disabled = false;
    }

    function confirmFocus() {
        if (!selectedQuestion || !currentStepData) {
            alert("Please process a thought and select a challenge question before continuing.");
            return;
        }

        conversationHistory.push({
            step: currentStep,
            thought: currentStepData.corrected_text,
            focus_question: selectedQuestion
        });
        currentStep++;
        
        appendToLog('AI', `You chose to focus on: "${selectedQuestion}"`, 'ai');
        appendToLog('SYSTEM', `Conversation Step ${currentStep}: Respond to the question above with your new thought.`, 'system');

        inputText.value = "";
        questionsContainer.style.display = 'none';
        guidedActions.style.display = 'none';
        selectedQuestionLabel.style.display = 'none';

        selectedQuestion = null;
        currentStepData = null;
        
        stopLoadingAnimation(`Conversation Step ${currentStep}: Enter your response to the question.`, 'var(--color-accent-orange)');
        setButtonsState(false); 
        confirmButton.disabled = true;
        
        saveCurrentSession();
    }
    
    async function generateBlogPost() {
        const lastThought = currentStepData?.corrected_text || inputText.value.trim();

        if (conversationHistory.length === 0 && !lastThought) {
            alert("You need to process at least one thought before generating a summary!");
            return;
        }
        
        setButtonsState(true);
        startLoadingAnimation("Compiling history and drafting blog post...");

        let conversationText = "Thought Process Transcript for Blog Post:\n\n";
        conversationHistory.forEach(item => {
            conversationText += `STEP ${item.step} - Thought/Response: ${item.thought}\n`;
            conversationText += `STEP ${item.step} - Focused Question: ${item.focus_question}\n\n`;
        });

        if (lastThought && currentStepData) {
             conversationText += `STEP ${currentStep} - Final Thought: ${lastThought}\n`;
        }
        
        try {
            // CALL FROM API.JS (Requires window.callGeminiApiPlain to be defined)
            const blogPostContent = await window.callGeminiApiPlain([{role: "user", text: conversationText}], BLOG_SYSTEM_INSTRUCTION);

            if (blogPostContent) {
                showModal("Generated Blog Post Summary", blogPostContent);
            } else {
                 alert("Failed to generate blog post.");
            }
        } catch (error) {
            alert("Error during blog generation: " + error.message);
        } finally {
            stopLoadingAnimation("Blog Post generated.");
            setButtonsState(false);
        }
    }
    
    // --- Debate Mode Methods ---

    async function startDebateMode() {
        if (isDebating) return;
        
        const claim = inputText.value.trim();
        if (!claim) {
            alert("Please enter your initial debate claim in the text box.");
            return;
        }
        
        currentSessionType = 'debate';
        sessionTitle = 'Debate: ' + claim.substring(0, 30) + (claim.length > 30 ? '...' : '');
        titleHeader.textContent = sessionTitle;
        
        showOpponentSelectionModal(claim);
    }

    async function sendDebateRebuttal() {
        if (!isDebating) return;

        const rebuttal = inputText.value.trim();
        if (!rebuttal) {
            alert("Please enter your rebuttal or argument.");
            return;
        }
        
        debateHistory.push({ role: "user", parts: [{ text: rebuttal }] });
        appendToLog('USER', rebuttal, 'user');
        inputText.value = ""; 
        
        saveCurrentSession();
        
        await getAiRebuttal();
    }

    async function getAiRebuttal() {
        if (!selectedOpponentKey) {
            alert("Debate opponent not selected. Please restart the debate process.");
            endDebate();
            return;
        }
        
        const opponentInstruction = DEBATE_OPPONENTS[selectedOpponentKey].instruction;
        const opponentName = DEBATE_OPPONENTS[selectedOpponentKey].name.split(' ')[0];

        setButtonsState(true);
        summarizeDebateButton.disabled = true; 
        startLoadingAnimation(`${opponentName} is formulating a rebuttal...`);

        try {
            // CALL FROM API.JS (Requires window.callGeminiApiPlain to be defined)
            const aiRebuttal = await window.callGeminiApiPlain(debateHistory, opponentInstruction);

            if (aiRebuttal && aiRebuttal !== "Failed to generate response.") {
                debateHistory.push({ role: "model", parts: [{ text: aiRebuttal }] });
                
                appendToLog('AI', aiRebuttal, 'debate');
                
                stopLoadingAnimation(`**${opponentName}** has responded. Enter your next rebuttal.`, 'var(--color-alert)');
                setButtonsState(false);
                summarizeDebateButton.disabled = false; 
                
                saveCurrentSession();

            } else {
                throw new Error("API returned an empty or invalid debate response.");
            }

        } catch (error) {
            stopLoadingAnimation("An API error occurred during the debate. Check console.", 'var(--color-alert)');
            setButtonsState(false);
            endDebateButton.disabled = false;
            console.error("Debate API Error:", error);
            alert("Debate API Error: " + error.message);
        }
    }
    
    async function summarizeDebate() {
        if (!isDebating || debateHistory.length < 2) {
            alert("The debate must have at least one user argument and one AI rebuttal to summarize.");
            return;
        }
        
        setButtonsState(true);
        startLoadingAnimation("Analyzing debate transcript and drafting summary...");
        
        let transcriptText = "Debate Transcript:\n\n";
        debateHistory.forEach(entry => {
            const role = entry.role === 'user' ? 'USER' : 'AI OPPONENT';
            transcriptText += `${role}: ${entry.parts[0].text}\n\n`;
        });
        
        try {
            // CALL FROM API.JS
            const summaryContent = await window.callGeminiApiPlain([{role: "user", parts: [{text: transcriptText}]}], SUMMARIZE_DEBATE_SYSTEM_INSTRUCTION);

            if (summaryContent) {
                showModal("Debate Summary", summaryContent);
            } else {
                 alert("Failed to generate debate summary.");
            }
        } catch (error) {
            alert("Error during summary generation: " + error.message);
        } finally {
            stopLoadingAnimation("Debate Summary generated.");
            setButtonsState(false);
        }
    }

    function endDebate() {
        if (!isDebating) return;
        
        saveCurrentSession();
        
        appendToLog('SYSTEM', 'The debate has concluded. Returning to Guided Exploration setup.', 'system');

        resetApp(true, true); 
        stopLoadingAnimation("Ready to start Guided Exploration or a new Debate.", null);
    }
    
    /** Resets all state and clears the log to a clean start. */
    function resetApp(clearLog = true, clearActiveStatus = true) {
        if (clearLog) {
            logContainer.innerHTML = `<div class="log-entry system" id="initial-system-message">
                Welcome! Enter your **initial thought** and click 'Process Thought' to start the Guided Exploration, OR enter a **debate claim** and click 'Start Debate Mode' to begin a debate.
            </div>`;
        }
        
        isDebating = false;
        conversationHistory = [];
        debateHistory = [];
        currentStep = 1;
        selectedQuestion = null;
        currentStepData = null;
        selectedOpponentKey = null;
        
        if (clearActiveStatus) {
            currentSessionId = null; 
            sessionTitle = 'New Session';
            titleHeader.textContent = sessionTitle;
            document.querySelectorAll('.session-item').forEach(item => item.classList.remove('active'));
        }

        questionsContainer.style.display = 'none';
        selectedQuestionLabel.style.display = 'none';
        guidedActions.style.display = 'none';
        debateActions.style.display = 'none';
        debateStartButton.style.display = 'inline-block';
        
        inputText.value = "";
        processButton.textContent = "Process Thought";
        processButton.classList.remove('accent-btn');
        processButton.classList.add('process-btn');
        setButtonsState(false);
    }


    // --- Initialization and Event Listeners ---
    
    initializeTheme();
    loadAllSessions(); 

    newChatButton.addEventListener('click', () => resetApp(true, true));
    
    // NEW DELEGATED LISTENER for sidebar
    sidebar.addEventListener('click', handleSidebarClick);

    processButton.addEventListener('click', processInput);
    debateStartButton.addEventListener('click', startDebateMode);
    confirmButton.addEventListener('click', confirmFocus);
    blogButton.addEventListener('click', generateBlogPost);
    summarizeDebateButton.addEventListener('click', summarizeDebate);
    endDebateButton.addEventListener('click', endDebate);
    themeToggleButton.addEventListener('click', toggleTheme);
    
    inputText.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey && !processButton.disabled) {
            e.preventDefault();
            if (isDebating) {
                sendDebateRebuttal();
            } else {
                processInput();
            }
        }
    });

    window.addEventListener('click', closeModal);


    // --- Public Interface ---
    return {
        closeModal: closeModal, 
        resetApp: () => resetApp(true, true) 
    };

})();