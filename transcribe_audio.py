import json
import time
import requests
import tkinter as tk
from tkinter import scrolledtext, messagebox, font as tkfont
import threading
import speech_recognition as sr 
import queue 

# --- Configuration ---
# NOTE: In a real application, the API Key should be loaded securely 
API_KEY = "" 
API_URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MODEL = "gemini-2.5-flash-preview-05-20" 
API_URL = f"{API_URL_BASE}/{MODEL}:generateContent?key={API_KEY}"

# --- System Instructions and JSON Schema (Unchanged) ---
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "corrected_text": {
            "type": "STRING",
            "description": "The cleaned, grammatically correct, and formal English version of the user's raw speech transcription."
        },
        "challenge_questions": {
            "type": "ARRAY",
            "description": "A list of exactly three thought-provoking questions designed to challenge the main assumption or explore the core idea of the corrected text further.",
            "items": {
                "type": "STRING"
            }
        }
    },
    "required": ["corrected_text", "challenge_questions"],
    "propertyOrdering": ["corrected_text", "challenge_questions"]
}

THOUGHT_COACH_SYSTEM_INSTRUCTION = (
    "You are a world-class language tutor and deep-thinking coach, similar to Ali Abdall's Voicepal. "
    "Your primary task is two-fold. "
    "First, take the raw, error-prone user transcription, correct all grammatical errors, smooth out "
    "pauses, filler words, and repetitions, and output it as clear, coherent, formal English text. "
    "Second, based *only* on the refined text, generate precisely 3 unique, thought-provoking questions. "
    "These questions must challenge the core assumption, explore the central idea's consequences, or push "
    "the user to consider the opposite perspective."
)

BLOG_SYSTEM_INSTRUCTION = (
    "You are a skilled content creator. Take the provided thought process, which is a sequence of initial thought and responses to challenge questions. "
    "Write a concise, engaging, and reflective blog post (3-4 paragraphs) that summarizes the core idea and the journey of exploration the user took. "
    "Use a positive and encouraging tone, suitable for a young audience, avoiding complex jargon."
    "Format the output as clear, clean text."
)

DEBATE_SYSTEM_INSTRUCTION = (
    "You are a skilled, highly intellectual devil's advocate. Your role is to debate the user's stance. "
    "Analyze the user's previous statement or argument. Generate a concise, intellectual, and challenging counter-argument or rebuttal. "
    "Do not agree with the user. Your response must continue the debate. "
    "Keep your response focused and always end by prompting the user for their next point. "
    "Maintain the persona of a rigorous academic opponent. Respond in plain text only."
)

# --- Core API Call Functions (Unchanged) ---

def call_gemini_api_structured(user_text, system_instruction, response_schema, max_retries=5):
    """Sends single-turn text to Gemini for structured output."""
    global API_URL
    if not API_KEY:
        raise ValueError("API Key is missing.")
        
    payload = {
        "contents": [{ "parts": [{ "text": user_text }] }],
        "systemInstruction": { "parts": [{ "text": system_instruction }] },
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": response_schema
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    
    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, headers=headers, data=json.dumps(payload))
            response.raise_for_status() 

            json_text = response.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text')
            
            if json_text:
                return json.loads(json_text)
            else:
                return None

        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            # Handle error and backoff
            wait_time = 2 ** attempt
            time.sleep(wait_time)

    return None

def call_gemini_api_debate(contents_list, system_instruction, max_retries=5):
    """Sends multi-turn chat history for plain text output (Debate Mode)."""
    global API_URL
    if not API_KEY:
        raise ValueError("API Key is missing.")

    # Convert debate_history into the required contents format
    contents = []
    for turn in contents_list:
        contents.append({
            "role": turn["role"],
            "parts": [{"text": turn["text"]}]
        })
        
    payload = {
        "contents": contents,
        "systemInstruction": { "parts": [{ "text": system_instruction }] },
    }

    headers = {'Content-Type': 'application/json'}

    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, headers=headers, data=json.dumps(payload))
            response.raise_for_status()

            # Return plain text response
            return response.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text')
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            # Handle error and backoff
            wait_time = 2 ** attempt
            time.sleep(wait_time)
            
    return None

# --- GUI Application Class ---

class VoicepalApp:
    def __init__(self, master):
        self.master = master
        master.title("Voicepal AI Thought Explorer")
        master.geometry("780x800") 
        master.grid_rowconfigure(0, weight=1)  # Conversation Log row
        master.grid_rowconfigure(1, weight=0)  # Controls/Input row
        master.grid_columnconfigure(0, weight=1)
        
        # --- MODERN DARK AESTHETICS (Monochromatic + Accent) ---
        self.BG_DARK = "#1A1A1A"        # Near Black / Main Background
        self.CARD_DARK = "#292929"      # Dark Gray / Layered Card Background
        self.TEXT_LIGHT = "#F0F0F0"     # Off White / Main Text
        self.ACCENT_COLOR = "#5DADE2"   # Soft Blue / Primary Accent & Focus
        self.SUCCESS_COLOR = "#52BE80"  # Soft Green / Confirm & Process
        self.ALERT_COLOR = "#E74C3C"    # Red / Recording Alert
        self.USER_MESSAGE_BG = "#343a40" # Slightly different dark tone for chat
        self.AI_MESSAGE_BG = "#292929"  # Use card dark for AI response
        self.BORDER_COLOR = "#444444"    # Subtle border for layered effect

        master.configure(bg=self.BG_DARK)

        # Speech Recognition setup
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_recording = False
        self.stop_listening = None 
        self.audio_queue = queue.Queue() 

        # Define custom fonts (Simulating Playfair Display and Lato)
        # Using Times (serif) for display and Helvetica (sans-serif) for body text
        self.display_font = "Times" # Playfair Display Simulation
        self.body_font = "Helvetica" # Lato Simulation
        
        self.header_font = tkfont.Font(family=self.display_font, size=24, weight="bold") 
        self.sub_header_font = tkfont.Font(family=self.body_font, size=14, weight="bold") 
        self.text_font = tkfont.Font(family=self.body_font, size=11)
        self.status_font = tkfont.Font(family=self.body_font, size=10, slant="italic")
        
        # --- Conversation State ---
        self.question_widgets = []
        self.last_selected_card = None
        self.selected_question = None 
        self.current_step_data = None 
        self.conversation_history = [] 
        self.current_step = 1 
        self.loading_active = False 
        self.loading_state = 0 
        
        # --- Debate State ---
        self.is_debating = False
        self.debate_history = [] 

        # --- 1. Conversation Log Area (Main Display - Uses scrollable text) ---
        # The log frame uses a minimal, flat style to simulate a clear glass/layered background
        log_frame = tk.Frame(master, bg=self.BG_DARK)
        log_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        self.conversation_log = scrolledtext.ScrolledText(
            log_frame, 
            wrap=tk.WORD, 
            width=60, 
            height=30, 
            font=self.text_font, 
            bg=self.BG_DARK, # Main background color for a transparent feel
            fg=self.TEXT_LIGHT, 
            bd=0, 
            relief=tk.FLAT, 
            padx=15, 
            pady=15, 
            state=tk.DISABLED
        )
        self.conversation_log.grid(row=0, column=0, sticky="nsew")

        # Define text tags for chat bubble simulation (rounded corners simulated with padding/background)
        self.conversation_log.tag_config('user_refined', background=self.USER_MESSAGE_BG, foreground=self.TEXT_LIGHT, lmargin1=20, lmargin2=20, rmargin=20, offset=5, justify='left', spacing1=5, spacing3=5)
        self.conversation_log.tag_config('ai_response', background=self.AI_MESSAGE_BG, foreground=self.TEXT_LIGHT, lmargin1=20, lmargin2=20, rmargin=20, offset=5, justify='left', spacing1=5, spacing3=5)
        self.conversation_log.tag_config('system_prompt', foreground=self.ACCENT_COLOR, font=self.sub_header_font, justify='center')
        self.conversation_log.tag_config('title', font=self.header_font, foreground=self.TEXT_LIGHT, justify='center')

        # Initial message
        self._append_to_log("SYSTEM", "Voicepal AI Thought Explorer\n", 'title', append_newline=False)
        self._append_to_log("SYSTEM", "Welcome! Start by recording or typing your initial thought below. The AI will refine it and offer challenge questions.", 'system_prompt')

        # --- 2. Control Panel (Below Log, static height) ---
        # Use a darker background with a subtle border for the 'layered' look
        self.control_panel = tk.Frame(master, bg=self.CARD_DARK, padx=15, pady=15, highlightbackground=self.BORDER_COLOR, highlightthickness=1)
        self.control_panel.grid(row=1, column=0, sticky="ew")
        self.control_panel.grid_columnconfigure(0, weight=1)
        
        # Inner Frame for Dynamic Elements (Questions/Actions)
        self.dynamic_control_frame = tk.Frame(self.control_panel, bg=self.CARD_DARK)
        self.dynamic_control_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 10))
        self.dynamic_control_frame.grid_columnconfigure(0, weight=1)

        # Question Display Area 
        self.questions_container = tk.Frame(self.dynamic_control_frame, bg=self.CARD_DARK)
        self.questions_container.grid(row=0, column=0, sticky="ew")
        self.questions_container.grid_columnconfigure(0, weight=1)
        self.questions_container.grid_remove() 
        
        self.selected_question_label = tk.Label(self.dynamic_control_frame, text="", font=self.text_font, bg=self.USER_MESSAGE_BG, fg=self.ACCENT_COLOR, wraplength=700, anchor="w", justify=tk.LEFT, padx=15, pady=10, bd=0, relief=tk.FLAT, highlightbackground=self.BORDER_COLOR, highlightthickness=1)
        self.selected_question_label.grid(row=1, column=0, pady=5, sticky="ew")
        self.selected_question_label.grid_remove()

        # Action Buttons Frame
        self.action_frame = tk.Frame(self.dynamic_control_frame, bg=self.CARD_DARK)
        self.action_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.action_frame.grid_columnconfigure(0, weight=1) # Confirm
        self.action_frame.grid_columnconfigure(1, weight=1) # Blog
        self.action_frame.grid_columnconfigure(2, weight=1) # Debate
        self.action_frame.grid_remove()
        
        # Helper function for button styling
        def create_styled_button(parent, text, command, bg_color, active_bg_color, initial_state):
            btn = tk.Button(parent, text=text, command=command, bg=bg_color, fg=self.TEXT_LIGHT, font=self.sub_header_font, relief=tk.FLAT, bd=0, padx=15, pady=10, activebackground=active_bg_color, state=initial_state)
            
            # Micro-interaction: Color transition on hover
            btn.bind("<Enter>", lambda e: btn.config(bg=active_bg_color))
            btn.bind("<Leave>", lambda e: btn.config(bg=bg_color))
            return btn

        # --- Button Calls (Corrected in previous step) ---
        # 1. Confirm Button
        self.confirm_button = create_styled_button(self.action_frame, "▶️ Confirm Focus & Continue", self.confirm_focus, self.SUCCESS_COLOR, "#4aa76f", tk.DISABLED)
        self.confirm_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        # 2. Blog Post Button
        self.blog_post_button = create_styled_button(self.action_frame, "📝 Generate Blog Post Summary", self.generate_blog_post_threaded, self.ACCENT_COLOR, "#4a9ac9", tk.DISABLED)
        self.blog_post_button.grid(row=0, column=1, sticky="ew", padx=(5, 5))

        # 3. Debate Button
        self.debate_button = create_styled_button(self.action_frame, "⚔️ Start Debate Mode", self.start_debate_mode, self.ACCENT_COLOR, "#4a9ac9", tk.DISABLED)
        self.debate_button.grid(row=0, column=2, sticky="ew", padx=(5, 0))


        # Input and Process Frame
        input_frame = tk.Frame(self.control_panel, bg=self.CARD_DARK)
        input_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        input_frame.grid_columnconfigure(0, weight=1)
        
        # Input Text Area (Simulating Glass/Layer with color contrast and border)
        self.input_text = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD, width=50, height=3, font=self.text_font, bg=self.USER_MESSAGE_BG, fg=self.TEXT_LIGHT, bd=0, relief=tk.FLAT, padx=15, pady=10, insertbackground=self.TEXT_LIGHT, highlightbackground=self.BORDER_COLOR, highlightthickness=1)
        self.input_text.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="ew")
        self.input_text.insert(tk.INSERT, "I think, uh, maybe all people should like, you know, work less time and be happier then. I want to talk more about this concept.")

        # Action Buttons
        # 4. Record Button (Note: The command is the toggle function)
        self.record_button = create_styled_button(input_frame, "🎤 Start Recording", self.record_input_toggle, self.ACCENT_COLOR, "#4a9ac9", tk.NORMAL)
        self.record_button.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="n")

        # 5. Process Button
        self.process_button = create_styled_button(input_frame, "✨ Process Thought", self.process_input_threaded, self.SUCCESS_COLOR, "#4aa76f", tk.NORMAL)
        self.process_button.grid(row=0, column=2, padx=(5, 0), pady=5, sticky="n")
        
        # Status Label
        self.status_label = tk.Label(self.control_panel, text="Ready to record or process existing text.", bg=self.CARD_DARK, fg="#adb5bd", font=self.status_font)
        self.status_label.grid(row=2, column=0, pady=(10, 0))


    # --- Animation and Status Management ---
    
    def start_loading_animation(self):
        """Starts the visual pulsing animation for AI processing."""
        self.loading_active = True
        self.process_button.config(text="Processing...", bg=self.ACCENT_COLOR, activebackground=self.ACCENT_COLOR, state=tk.DISABLED)
        self._animate_loading()

    def _animate_loading(self):
        """Recursively updates the status label text for the loading effect."""
        if not self.loading_active:
            return
        
        dots = "." * (self.loading_state % 4)
        status_message = "AI is thinking" + dots
        # Use a high contrast color for the loading state
        self.status_label.config(text=status_message, fg=self.ACCENT_COLOR)
        self.loading_state += 1
        # Subtle animation speed
        self.master.after(300, self._animate_loading) 

    def stop_loading_animation(self, final_text, final_color="#adb5bd"):
        """Stops the loading animation and sets the final status text."""
        self.loading_active = False
        self.loading_state = 0
        self.status_label.config(text=final_text, fg=final_color)
        
        # Reset process button text based on mode
        # THIS IS WHERE THE SYNTAX ERROR LIKELY OCCURRED, NOW CLEANED:
        if self.is_debating:
            self.process_button.config(text="💬 Send Rebuttal", bg=self.ACCENT_COLOR, activebackground="#4a9ac9")
        else:
            self.process_button.config(text="✨ Process Thought", bg=self.SUCCESS_COLOR, activebackground="#4aa76f")
        

    # --- Chat Log Management ---

    def _append_to_log(self, sender, text, tag_name, append_newline=True):
        """Appends text to the conversation log with specific styling and scrolls to the end."""
        self.conversation_log.config(state=tk.NORMAL)
        
        if sender == "USER":
            prefix = "YOU (Refined): "
            tag = 'user_refined'
        elif sender == "AI":
            prefix = "AI Coach: "
            tag = 'ai_response'
        elif sender == "DEBATE":
            prefix = "AI Opponent: "
            tag = 'ai_response'
        elif sender == "SYSTEM":
            prefix = ""
            tag = tag_name # Use tag_name directly for system tags

        if append_newline:
            # Add an extra newline for separation between chat bubbles/segments
            full_text = f"\n{prefix}{text}\n"
        else:
            full_text = f"{prefix}{text}"

        self.conversation_log.insert(tk.END, full_text, tag)
        self.conversation_log.see(tk.END)
        self.conversation_log.config(state=tk.DISABLED)

    # --- Mode Management ---

    def set_gui_mode(self, mode):
        """Switches the UI context between 'GUIDED' and 'DEBATE'."""
        if mode == 'GUIDED':
            self.is_debating = False
            self.process_button.config(text="✨ Process Thought", command=self.process_input_threaded, bg=self.SUCCESS_COLOR, activebackground="#4aa76f")
            self.debate_button.config(text="⚔️ Start Debate Mode", command=self.start_debate_mode, state=tk.DISABLED, bg=self.ACCENT_COLOR, activebackground="#4a9ac9")
            # Re-show all guided controls
            self.questions_container.grid()
            self.selected_question_label.grid()
            self.action_frame.grid()
            self.create_question_cards([])
        
        elif mode == 'DEBATE':
            self.is_debating = True
            self.debate_history = []
            self.process_button.config(text="💬 Send Rebuttal", command=self.send_rebuttal_threaded, bg=self.ACCENT_COLOR, activebackground="#4a9ac9")
            
            # Hide guided mode elements
            self.questions_container.grid_remove() 
            self.selected_question_label.grid_remove()
            self.confirm_button.grid_remove()
            self.blog_post_button.grid_remove()
            
            # Update Debate button to show exit option (remains visible in action_frame)
            self.debate_button.config(text="❌ End Debate", command=self.end_debate, state=tk.NORMAL, bg=self.ALERT_COLOR, activebackground="#c0392b")


    # --- STT Methods (Unchanged) ---
    def speech_callback(self, recognizer, audio):
        """Callback function for background listening. Transcribes the audio."""
        try:
            transcription = recognizer.recognize_google(audio)
            self.audio_queue.put({"status": "SUCCESS", "text": transcription})
        except sr.UnknownValueError:
            self.audio_queue.put({"status": "UNKNOWN"})
        except sr.RequestError as e:
            self.audio_queue.put({"status": "ERROR_REQUEST", "error": f"Request failed: {e}"})
        except Exception as e:
            self.audio_queue.put({"status": "ERROR_GENERAL", "error": f"General error: {e}"})
        
        self.master.after(100, self.process_transcription_from_queue)

    def record_input_toggle(self):
        """Toggles the recording state and starts/stops background listening."""
        if not self.is_recording:
            self.is_recording = True
            
            self.input_text.delete(1.0, tk.END)
            self.process_button.config(state=tk.DISABLED)
            
            self.stop_listening = self.recognizer.listen_in_background(
                self.microphone, 
                self.speech_callback
            )
            
            # Use ALERT_COLOR for active recording
            self.record_button.config(text="🔴 Stop Recording", bg=self.ALERT_COLOR, activebackground="#c0392b")
            self.status_label.config(text="Listening... Click 'Stop Recording' to end and transcribe.", fg=self.ALERT_COLOR)

        else:
            self.is_recording = False
            
            if self.stop_listening:
                self.stop_listening(wait_for_stop=False) 
                self.stop_listening = None

            # Reset to ACCENT_COLOR
            self.record_button.config(text="🎤 Start Recording", bg=self.ACCENT_COLOR, activebackground="#4a9ac9")
            self.status_label.config(text="Recording stopped. Waiting for transcription from background thread...", fg=self.ACCENT_COLOR)
            
    def process_transcription_from_queue(self):
        """Checks the queue for the transcription result and updates the UI."""
        self.process_button.config(state=tk.NORMAL)

        try:
            result = self.audio_queue.get_nowait()
        except queue.Empty:
            return

        status = result.get("status")
        
        if status == "SUCCESS":
            transcription = result.get("text")
            self.input_text.delete(1.0, tk.END)
            self.input_text.insert(tk.INSERT, transcription)
            self.stop_loading_animation("Transcription ready. Click 'Process' to analyze.", self.SUCCESS_COLOR)
        elif status == "UNKNOWN":
            self.stop_loading_animation("Could not understand audio. Ready to process!", self.ALERT_COLOR)
            messagebox.showwarning("Error", "Speech Recognition could not understand the audio.")
        elif status == "ERROR_REQUEST":
            self.stop_loading_animation("STT Service Failed. Ready to process!", self.ALERT_COLOR)
            messagebox.showerror("STT Error", f"Could not request results from STT service; {result.get('error')}")
        elif status == "ERROR_GENERAL":
             self.stop_loading_animation("An error occurred during recording. Ready to process!", self.ALERT_COLOR)
             messagebox.showerror("Error", f"An unexpected error occurred: {result.get('error')}")
    
    # --- Guided Mode Methods ---

    def create_question_cards(self, questions):
        """Generates dynamic, clickable card-style frames for each challenge question."""
        for widget in self.question_widgets:
            widget.destroy()
        self.question_widgets = []
        self.last_selected_card = None
        
        self.selected_question = None
        self.selected_question_label.config(text="Select one of the challenge questions below to focus your next response.", bg=self.CARD_DARK, fg=self.TEXT_LIGHT)
        self.selected_question_label.grid()
        self.confirm_button.config(state=tk.DISABLED)
        self.action_frame.grid()
        self.questions_container.grid()
        
        DEFAULT_CARD_BG = self.CARD_DARK
        HOVER_CARD_BG = "#343a40" # Slight hover effect
        SELECTED_CARD_BORDER = self.SUCCESS_COLOR

        for i, question_text in enumerate(questions):
            # Clean card style - uses highlight for border (simulating rounded corners/layer)
            card_frame = tk.Frame(self.questions_container, bg=DEFAULT_CARD_BG, bd=0, relief=tk.FLAT, padx=15, pady=15, highlightbackground=self.BORDER_COLOR, highlightthickness=1)
            card_frame.grid(row=i, column=0, sticky="ew", pady=5)
            card_frame.grid_columnconfigure(1, weight=1) 
            self.question_widgets.append(card_frame)

            icon_label = tk.Label(card_frame, text=f"Q{i + 1}", font=self.sub_header_font, bg=self.ACCENT_COLOR, fg="white", padx=10, pady=5, relief=tk.FLAT)
            icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 10))

            q_label = tk.Label(card_frame, text=question_text, font=self.text_font, bg=DEFAULT_CARD_BG, fg=self.TEXT_LIGHT, wraplength=650, justify=tk.LEFT, anchor="w", padx=0, pady=0)
            q_label.grid(row=0, column=1, sticky="ew")

            click_handler = lambda e, text=question_text, frame=card_frame: self.select_question(text, frame)
            
            # Hover effects for visual feedback (micro-interaction)
            def on_enter(e, frame=card_frame):
                if frame != self.last_selected_card:
                    frame.config(bg=HOVER_CARD_BG)
                    e.widget.config(bg=HOVER_CARD_BG)

            def on_leave(e, frame=card_frame):
                 if frame != self.last_selected_card:
                    frame.config(bg=DEFAULT_CARD_BG)
                    e.widget.config(bg=DEFAULT_CARD_BG)
            
            # Bind events to all components of the card for easy clicking/hovering
            for widget in [card_frame, q_label, icon_label]:
                widget.bind("<Button-1>", click_handler)
                widget.bind("<Enter>", on_enter)
                widget.bind("<Leave>", on_leave)
                # Ensure the background is the same for the label to allow the frame hover to work
                if widget != card_frame:
                    widget.config(bg=DEFAULT_CARD_BG) 
            
        # Scroll to the latest question cards
        self.conversation_log.see(tk.END)


    def select_question(self, question_text, current_card):
        """Highlights the selected question card and updates the 'Next Focus' area."""
        
        DEFAULT_CARD_BG = self.CARD_DARK
        SELECTED_CARD_BORDER = self.SUCCESS_COLOR
        
        # Deselect the previous card
        if self.last_selected_card:
            self.last_selected_card.config(highlightbackground=self.BORDER_COLOR, highlightthickness=1, bg=DEFAULT_CARD_BG)
            # Find and update child labels too
            for child in self.last_selected_card.winfo_children():
                if child.cget('bg') != self.ACCENT_COLOR: # Don't change icon color
                    child.config(bg=DEFAULT_CARD_BG)


        # Select the new card
        current_card.config(highlightbackground=SELECTED_CARD_BORDER, highlightthickness=2, bg=self.USER_MESSAGE_BG)
        # Update child labels
        for child in current_card.winfo_children():
            if child.cget('bg') != self.ACCENT_COLOR: # Don't change icon color
                child.config(bg=self.USER_MESSAGE_BG)
                
        self.last_selected_card = current_card

        self.selected_question = question_text 
        self.selected_question_label.config(
            text=f"Selected Focus: {question_text}", 
            bg=self.USER_MESSAGE_BG, 
            fg=self.SUCCESS_COLOR,
            highlightbackground=self.SUCCESS_COLOR,
            highlightthickness=1
        )
        self.confirm_button.config(state=tk.NORMAL)

    def confirm_focus(self):
        """Confirms selection, saves state, and prepares for the next step in guided mode."""
        if not self.selected_question or not self.current_step_data:
            messagebox.showwarning("Incomplete Data", "Please process a thought and select a challenge question before continuing.")
            return

        # 1. Add current thought/response to history
        self.conversation_history.append({
            "step": self.current_step,
            "thought": self.current_step_data.get("corrected_text", "N/A"),
            "focus_question": self.selected_question
        })
        self.current_step += 1
        
        # 2. Append the selected focus question to the log
        self._append_to_log("AI", f"You chose to focus on: \"{self.selected_question}\"", 'ai_response')
        self._append_to_log("SYSTEM", f"Conversation Step {self.current_step}: Respond to the question above with your new thought.", 'system_prompt')

        # 3. Reset UI for new input
        self.input_text.delete(1.0, tk.END)
        self.input_text.insert(tk.INSERT, "Enter your response here...")
        
        # 4. Hide question cards and actions until the next process
        for widget in self.question_widgets:
            widget.destroy()
        self.question_widgets = []
        self.questions_container.grid_remove()
        self.action_frame.grid_remove()
        self.selected_question_label.grid_remove()

        self.selected_question = None
        self.current_step_data = None
        
        # Update status and re-enable debate/blog buttons
        self.stop_loading_animation(f"Conversation Step {self.current_step}: Record your response.")
        self.debate_button.config(state=tk.NORMAL)
        self.blog_post_button.config(state=tk.NORMAL)
        
        self.conversation_log.see(tk.END)

    # --- Blog Post Generation (Unchanged logic, updated aesthetics) ---

    def generate_blog_post_threaded(self):
        """Starts blog post generation in a separate thread."""
        last_thought = self.current_step_data.get("corrected_text") if self.current_step_data else None

        if not self.conversation_history and not last_thought:
            messagebox.showwarning("No History", "You need to process at least one thought before generating a summary!")
            return
            
        self.set_buttons_state(tk.DISABLED, "")
        self.start_loading_animation()
        
        threading.Thread(target=self._run_blog_post_generation, daemon=True).start()

    def _run_blog_post_generation(self):
        """Worker function to compile history and call the plain text API for the blog post."""
        conversation_text = "Thought Process Transcript for Blog Post:\n\n"
        for item in self.conversation_history:
            conversation_text += f"STEP {item['step']} - Thought/Response: {item['thought']}\n"
            conversation_text += f"STEP {item['step']} - Focused Question: {item['focus_question']}\n\n"

        # Capture the final processed thought if it exists and wasn't followed up
        final_thought = self.current_step_data.get("corrected_text", "N/A") if self.current_step_data else None
        if final_thought and final_thought != "N/A":
             conversation_text += f"STEP {self.current_step} - Final Thought: {final_thought}\n"
        
        try:
            blog_post_content = call_gemini_api_debate([{"role": "user", "text": conversation_text}], BLOG_SYSTEM_INSTRUCTION)
        except ValueError as e:
            self.master.after(0, lambda: messagebox.showerror("API Error", str(e)))
            blog_post_content = "Failed due to configuration error."
            
        if not blog_post_content:
            blog_post_content = "Failed to generate blog post after multiple retries. Check connection or API key."

        self.master.after(0, lambda: self._show_blog_post_window(blog_post_content))

    def _show_blog_post_window(self, content):
        """Displays the generated blog post in a new modal window and re-enables buttons."""
        self.stop_loading_animation("Blog Post generated.")
        self.set_buttons_state(tk.NORMAL)
        
        # --- Modal Window Styling (matches dark theme) ---
        top = tk.Toplevel(self.master)
        top.title("Generated Blog Post Summary")
        top.configure(bg=self.CARD_DARK)
        
        window_width = 650
        window_height = 550
        x = (self.master.winfo_screenwidth() / 2) - (window_width / 2)
        y = (self.master.winfo_screenheight() / 2) - (window_height / 2)
        top.geometry('%dx%d+%d+%d' % (window_width, window_height, x, y))
        
        tk.Label(top, text="Your Thought Journey Summary", font=self.sub_header_font, bg=self.CARD_DARK, fg=self.TEXT_LIGHT, pady=15).pack(fill='x', padx=10)

        # Scrolled Text Box using dark tones
        post_text = scrolledtext.ScrolledText(top, wrap=tk.WORD, width=70, height=20, font=self.text_font, bg=self.USER_MESSAGE_BG, fg=self.TEXT_LIGHT, bd=0, relief=tk.FLAT, padx=20, pady=20)
        post_text.insert(tk.INSERT, content)
        post_text.config(state=tk.DISABLED)
        post_text.pack(fill='both', expand=True, padx=20, pady=10)

        # Close Button
        close_btn = tk.Button(top, text="Close", command=top.destroy, bg=self.ACCENT_COLOR, fg="white", font=self.sub_header_font, relief=tk.FLAT, padx=15, pady=8, activebackground="#4a9ac9")
        close_btn.bind("<Enter>", lambda e: close_btn.config(bg="#4a9ac9"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(bg=self.ACCENT_COLOR))
        close_btn.pack(pady=(0, 20))
        
    # --- Debate Mode Methods (Unchanged logic, updated aesthetics) ---

    def start_debate_mode(self):
        """Initializes the debate mode with the user's final corrected thought."""
        initial_argument = self.current_step_data.get("corrected_text") if self.current_step_data else None
        
        if not initial_argument or initial_argument == "N/A":
            messagebox.showwarning("No Argument", "Please process a thought first and ensure the corrected output is not empty before starting a debate.")
            return

        self.set_gui_mode('DEBATE')
        self._append_to_log("SYSTEM", "⚔️ Entering Debate Mode ⚔️", 'system_prompt')
        self._append_to_log("SYSTEM", f"Starting debate on your refined statement: \"{initial_argument}\"", 'ai_response')
        
        # 1. Add user's first argument to debate history
        self.debate_history.append({"role": "user", "text": initial_argument})
        
        # 2. Clear input area for debate
        self.input_text.delete(1.0, tk.END)
        self.input_text.insert(tk.INSERT, "Enter your counter-argument here...")

        # 3. Thread the first AI turn
        self.send_rebuttal_threaded()
        
        self.conversation_log.see(tk.END)

    def end_debate(self):
        """Ends the debate and returns the UI to the clean guided mode starting state."""
        self.set_gui_mode('GUIDED')
        
        self._append_to_log("SYSTEM", "Debate Ended. Returning to Thought Exploration Mode.", 'system_prompt')
        
        # Clear all debate-specific data and reset to initial state
        self.debate_history = []
        self.current_step = 1
        self.conversation_history = []
        self.current_step_data = None
        
        self.input_text.delete(1.0, tk.END)
        self.input_text.insert(tk.INSERT, "Start a new thought here...")
        
        self.stop_loading_animation("Debate ended. Ready to start a new thought exploration!")
        self.process_button.config(state=tk.NORMAL) 
        self.debate_button.config(state=tk.DISABLED) 
        
        self.conversation_log.see(tk.END)


    def send_rebuttal_threaded(self):
        """Starts the debate turn in a separate thread."""
        user_rebuttal = self.input_text.get(1.0, tk.END).strip()
        
        # Check if it's a subsequent turn and the user hasn't typed anything new
        if len(self.debate_history) > 1 and (not user_rebuttal or user_rebuttal == "Enter your counter-argument here..."):
            messagebox.showwarning("Missing Rebuttal", "Please enter your response to the AI's argument.")
            return

        if len(self.debate_history) > 1: # Only for subsequent turns
            self.debate_history.append({"role": "user", "text": user_rebuttal})
            self._append_to_log("USER", user_rebuttal, 'user_refined') # Show user's rebuttal in log
        
        self.set_buttons_state(tk.DISABLED, "")
        self.start_loading_animation()
        self.input_text.delete(1.0, tk.END) # Clear input after sending
        
        threading.Thread(target=self._run_debate_turn, daemon=True).start()

    def _run_debate_turn(self):
        """Worker function to call the debate API and update the UI."""
        try:
            ai_rebuttal = call_gemini_api_debate(self.debate_history, DEBATE_SYSTEM_INSTRUCTION)
        except ValueError as e:
            self.master.after(0, lambda: messagebox.showerror("API Error", str(e)))
            ai_rebuttal = "Debate turn failed due to configuration error."

        if not ai_rebuttal:
            ai_rebuttal = "AI failed to generate a rebuttal after multiple retries. Try ending and restarting the debate."

        self.debate_history.append({"role": "assistant", "text": ai_rebuttal})
        
        self.master.after(0, lambda: self._update_debate_ui(ai_rebuttal))


    def _update_debate_ui(self, ai_rebuttal):
        """Updates the UI after the AI generates a rebuttal in Debate Mode."""
        
        self.stop_loading_animation("Your turn! Enter your rebuttal and click 'Send Rebuttal'.", self.ACCENT_COLOR)
        
        self._append_to_log("DEBATE", ai_rebuttal, 'ai_response')
        
        self.input_text.config(state=tk.NORMAL)
        self.input_text.delete(1.0, tk.END)
        self.input_text.insert(tk.INSERT, "Enter your counter-argument here...")
        self.input_text.config(state=tk.NORMAL)
        
        self.set_buttons_state(tk.NORMAL, "")
        self.debate_button.config(text="❌ End Debate", command=self.end_debate, state=tk.NORMAL, bg=self.ALERT_COLOR, activebackground="#c0392b")
        
        self.conversation_log.see(tk.END)

    # --- Shared Utility Methods ---

    def set_buttons_state(self, state, status_text=""):
        """Utility to disable/enable all main action buttons."""
        # Note: If state is DISABLED, the record button must be handled carefully to allow stopping a recording
        if state == tk.DISABLED and self.is_recording:
             # If recording, only disable all other buttons, leave record button enabled to stop it
             self.process_button.config(state=state)
             self.confirm_button.config(state=state)
             self.blog_post_button.config(state=state)
             self.debate_button.config(state=state)
             # Leave record_button active
        else:
            self.process_button.config(state=state)
            self.confirm_button.config(state=state)
            self.blog_post_button.config(state=state)
            self.debate_button.config(state=state)
            self.record_button.config(state=state)
            
        if status_text:
            self.status_label.config(text=status_text)
            
    def process_input_threaded(self):
        """Starts the API call in a separate thread for the Guided Mode."""
        
        raw_text = self.input_text.get(1.0, tk.END).strip()
        
        if not raw_text or raw_text.startswith("Start a new thought here...") or raw_text.startswith("Enter your response here...") or raw_text.startswith("Enter your counter-argument here..."):
            messagebox.showwarning("Missing Input", "Please record or type your thought before processing.")
            return

        self.set_buttons_state(tk.DISABLED, "")
        self.start_loading_animation()
        
        threading.Thread(target=self._run_thought_processing, args=(raw_text,), daemon=True).start()

    def _run_thought_processing(self, raw_text):
        """Worker function to call the structured API."""
        try:
            result = call_gemini_api_structured(
                raw_text, 
                THOUGHT_COACH_SYSTEM_INSTRUCTION, 
                RESPONSE_SCHEMA
            )
            
            if result:
                self.master.after(0, lambda: self._update_guided_result(raw_text, result))
            else:
                self.master.after(0, lambda: self._handle_error("API returned no content or failed to parse JSON."))
                
        except ValueError as e:
            self.master.after(0, lambda: self._handle_error(str(e)))
        except Exception as e:
            self.master.after(0, lambda: self._handle_error(f"An unexpected error occurred: {e}"))

    def _update_guided_result(self, raw_text, result):
        """Updates UI elements in the main thread with processed results (Guided Mode)."""
        self.current_step_data = result
        
        corrected_text = result.get('corrected_text', 'Correction failed.')
        challenge_questions = result.get('challenge_questions', [])
        
        self.input_text.delete(1.0, tk.END)
        self.input_text.insert(tk.INSERT, "Enter your response here...")
        self.stop_loading_animation("Thought processed. Select a question to focus on or start a debate.", self.SUCCESS_COLOR)
        
        self.create_question_cards(challenge_questions)
        
        self.set_buttons_state(tk.NORMAL, "")
        self.process_button.config(state=tk.NORMAL) 
        
        self.debate_button.config(state=tk.NORMAL)
        self.blog_post_button.config(state=tk.NORMAL if self.conversation_history else tk.DISABLED)

        # 1. Append the refined thought to the log LAST, after the UI updates are complete
        self._append_to_log("USER", corrected_text, 'user_refined')
        
        # 2. Append the AI's question prompt to the log
        self._append_to_log("AI", "Your thought has been refined. Choose one of the challenge questions below to continue your exploration.", 'ai_response')

    def _handle_error(self, message):
        """Handles errors and re-enables buttons."""
        self._append_to_log("SYSTEM", f"ERROR: Processing failed: {message}", 'ai_response')
        self.stop_loading_animation("Processing failed. See log for details.", self.ALERT_COLOR)
        self.set_buttons_state(tk.NORMAL, "")
        messagebox.showerror("Processing Error", message)

if __name__ == '__main__':
    root = tk.Tk()
    app = VoicepalApp(root)
    root.mainloop()
