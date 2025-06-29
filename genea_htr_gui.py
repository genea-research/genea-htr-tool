#!/usr/bin/env python3
"""
Genealogy Assistant AI Handwritten Text Recognition Tool - Genea.ca
Copyright (C) 2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
"""
Handwriting transcription script using multiple AI APIs
Processes JPEG, PNG, and PDF files, transcribes handwriting, and creates searchable PDFs.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import tkinterdnd2 as tkdnd
import os
import sys
import threading
import json
from pathlib import Path
from typing import Dict, List
import queue
import time
import webbrowser
from PIL import Image, ImageTk
import logging
from datetime import datetime
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import the existing OCR functionality
from genea_htr import HandwritingOCR

# Application version
VERSION = "0.3.4"


class BaseDialog(tk.Toplevel):
    """Base class for dialog windows."""
    def __init__(self, parent, title, min_width=600, min_height=400, resizable=(True, True)):
        super().__init__(parent)
        self.parent = parent  # Store parent reference
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.configure(bg="#2b2b2b")
        self.result = None

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.center_dialog(parent, min_width, min_height)
        self.resizable(resizable[0], resizable[1])

    def center_dialog(self, parent, min_width, min_height):
        """Center the dialog on the parent window."""
        self.update_idletasks()
        
        dialog_width = max(min_width, self.winfo_reqwidth())
        dialog_height = max(min_height, self.winfo_reqheight())

        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        x = parent_x + (parent_width // 2) - (dialog_width // 2)
        y = parent_y + (parent_height // 2) - (dialog_height // 2)

        self.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        self.minsize(min_width, min_height)

    def cancel(self):
        """Default cancel action."""
        self.destroy()


class LogHandler(logging.Handler):
    """Custom logging handler that sends log messages to a queue for GUI display."""
    
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
        
    def emit(self, record):
        """Send log record to the queue."""
        try:
            # Format the log message with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"[{timestamp}] {record.getMessage()}"
            self.log_queue.put(message)
        except Exception:
            # Don't let logging errors crash the application
            pass


class LogViewerDialog(BaseDialog):
    """Dialog for viewing real-time logs."""
    
    def __init__(self, parent, log_queue, on_close=None):
        super().__init__(parent, "Processing Logs", min_width=800, min_height=600)
        
        self.log_queue = log_queue
        self.on_close_callback = on_close
        self.running = True
        
        # Override default close behavior
        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.create_widgets()
        self.start_log_monitoring()
        
    def create_widgets(self):
        """Create the log viewer interface."""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(main_frame, text="Real-time Processing Logs", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Log text area with scrollbar
        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            bg="#1e1e1e",
            fg="#ffffff",
            insertbackground="#ffffff",
            selectbackground="#404040",
            font=("Consolas", 16),
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Close", command=self.cancel, style='Rounded.TButton').pack(side=tk.RIGHT)
        
        # Auto-scroll checkbox
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(button_frame, text="Auto-scroll", variable=self.auto_scroll_var, style='TCheckbutton').pack(side=tk.RIGHT, padx=(0, 10))
        
    def start_log_monitoring(self):
        """Start monitoring the log queue for new messages."""
        self.check_log_queue()
        
    def check_log_queue(self):
        """Check for new log messages and update the display."""
        if not self.running:
            return
            
        try:
            # Process all available log messages
            while True:
                try:
                    message = self.log_queue.get_nowait()
                    self.add_log_message(message)
                except queue.Empty:
                    break
        except Exception as e:
            # Don't let queue errors crash the dialog
            pass
        
        # Schedule next check
        if self.running:
            self.after(100, self.check_log_queue)
    
    def add_log_message(self, message):
        """Add a log message to the display."""
        try:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            
            # Auto-scroll to bottom if enabled
            if self.auto_scroll_var.get():
                self.log_text.see(tk.END)
                
            self.log_text.config(state=tk.DISABLED)
        except Exception:
            # Don't let text widget errors crash the dialog
            pass
    
    def cancel(self):
        """Close the log viewer dialog."""
        self.running = False
        if self.on_close_callback:
            self.on_close_callback()
        super().cancel()


def get_resource_path(relative_path):
    """Get the absolute path to a resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        
        # Try multiple possible locations for the resource
        possible_paths = []
        
        # For macOS app bundles, resources are in Resources folder
        if sys.platform == 'darwin':
            possible_paths.append(os.path.join(base_path, 'Resources', relative_path))
        
        # For Windows/Linux, try both root and Resources folder
        possible_paths.extend([
            os.path.join(base_path, relative_path),
            os.path.join(base_path, 'Resources', relative_path)
        ])
        
        # Return the first path that exists
        for path in possible_paths:
            if os.path.exists(path):
                return path
                
        # If none exist, return the first option as fallback
        return possible_paths[0] if possible_paths else os.path.join(base_path, relative_path)
        
    except AttributeError:
        # Running in development mode
        return os.path.join(os.path.abspath("."), relative_path)


def get_settings_path():
    """Get the appropriate path for saving settings files based on the platform."""
    try:
        # Check if we're running as a PyInstaller bundle
        if hasattr(sys, '_MEIPASS'):
            # Running as bundled app
            if sys.platform == 'darwin':
                # macOS: Use user's Application Support directory
                home = os.path.expanduser("~")
                app_support = os.path.join(home, "Library", "Application Support", "GeneaHTR")
                os.makedirs(app_support, exist_ok=True)
                return os.path.join(app_support, "htr_settings.json")
            elif sys.platform == 'win32':
                # Windows: Use AppData/Local directory
                appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser("~"))
                app_dir = os.path.join(appdata, "GeneaHTR")
                os.makedirs(app_dir, exist_ok=True)
                return os.path.join(app_dir, "htr_settings.json")
            else:
                # Linux: Use ~/.config directory
                home = os.path.expanduser("~")
                config_dir = os.path.join(home, ".config", "GeneaHTR")
                os.makedirs(config_dir, exist_ok=True)
                return os.path.join(config_dir, "htr_settings.json")
        else:
            # Running in development mode - use current directory
            return "htr_settings.json"
    except Exception as e:
        print(f"Error determining settings path: {e}")
        # Fallback to current directory
        return "htr_settings.json"


class SettingsDialog(BaseDialog):
    """Dialog for editing settings."""
    
    def __init__(self, parent, provider_configs: Dict, general_settings: Dict = None):
        super().__init__(parent, "Edit Settings", min_width=900, min_height=700)

        self.provider_configs = provider_configs.copy()  # Work with a copy
        self.general_settings = general_settings.copy() if general_settings else {"max_workers": 1}

        self.create_widgets()

        # Force initial update of all tabs after a short delay
        self.after(100, self.force_initial_update)
        # Additional delay to ensure canvas layout is complete
        self.after(200, self.force_canvas_layout)

    def create_widgets(self):
        """Create the settings interface."""
        # Main frame with scrollbar
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Provider tabs
        provider_display_names = {"openai": "OpenAI", "anthropic": "Anthropic", "openrouter": "OpenRouter", "google": "Google"}
        for provider in ["openai", "anthropic", "openrouter", "google"]:
            provider_frame = ttk.Frame(notebook)
            notebook.add(provider_frame, text=provider_display_names[provider])
            self.create_provider_settings(provider_frame, provider)
        
        # General settings tab
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="General")
        self.create_general_settings(general_frame)
        
        # Bind tab change event to refresh canvas
        notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.notebook = notebook
        
        # Also bind to selection events for immediate response
        def on_tab_select(event):
            # Force immediate update when tab is selected
            self.after_idle(lambda: self.on_tab_changed(event))
        notebook.bind("<Button-1>", on_tab_select)
        
        # Force initial update of all tabs after a short delay
        self.after(100, self.force_initial_update)
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(6, 0))
        
        ttk.Button(button_frame, text="Save", command=self.save_settings, style='Rounded.TButton').pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=self.cancel, style='Rounded.TButton').pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_defaults, style='Rounded.TButton').pack(side=tk.LEFT)
        
    def create_provider_settings(self, parent, provider):
        """Create settings widgets for a provider."""
        # Create scrollable frame
        canvas = tk.Canvas(parent, bg="#2b2b2b", highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Create canvas window and store reference
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        def configure_scroll_region(event=None):
            """Update scroll region when scrollable frame changes."""
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def configure_canvas_width(event=None):
            """Update scrollable frame width to match canvas width."""
            canvas_width = canvas.winfo_width()
            if canvas_width > 1:  # Only update if canvas has valid width
                canvas.itemconfig(canvas_window, width=canvas_width)
                # Force immediate redraw
                canvas.update_idletasks()
                scrollable_frame.update_idletasks()
        
        # Bind events for proper scrolling and width management
        scrollable_frame.bind("<Configure>", configure_scroll_region)
        canvas.bind("<Configure>", configure_canvas_width)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", on_mousewheel)
        
        # Add visibility event handlers to ensure content is displayed
        def on_canvas_map(event):
            """Handle canvas being mapped (becoming visible)."""
            canvas.update_idletasks()
            scrollable_frame.update_idletasks()
            canvas.event_generate('<Configure>')
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def on_canvas_visibility(event):
            """Handle canvas visibility changes."""
            if event.state == "VisibilityUnobscured":
                canvas.update_idletasks()
                canvas.configure(scrollregion=canvas.bbox("all"))
        
        canvas.bind("<Map>", on_canvas_map)
        canvas.bind("<Visibility>", on_canvas_visibility)
        
        # Get provider config
        config = self.provider_configs.get(provider, {
            "api_key": "",
            "primary": {"model": "", "prompt": ""},
            "fallback": {"model": "", "prompt": ""}
        })
        
        # API Key section
        api_frame = tk.Frame(scrollable_frame, bg="#212121", bd=1, relief="solid", highlightbackground="#555555")
        api_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        # Proper display names for section titles
        provider_names = {"openai": "OpenAI", "anthropic": "Anthropic", "openrouter": "OpenRouter"}
        display_name = provider_names.get(provider, provider.title())
        api_label = tk.Label(api_frame, text=f"{display_name} API Configuration", 
                           bg="#212121", fg="#ffffff", font=("Arial", 14, "bold"))
        api_label.pack(anchor="nw", padx=10, pady=(5, 0))
        
        api_inner = tk.Frame(api_frame, bg="#212121")
        api_inner.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Label(api_inner, text="API Key:", bg="#212121", fg="#ffffff", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        api_key_var = tk.StringVar(value=config.get("api_key", ""))
        api_key_entry = ttk.Entry(api_inner, textvariable=api_key_var, show="*", width=50, style='Borderless.TEntry')
        api_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        setattr(self, f"{provider}_api_key_var", api_key_var)
        
        # Primary model section
        self.create_model_section(scrollable_frame, provider, "primary", config.get("primary", {}))
        
        # Fallback model section
        self.create_model_section(scrollable_frame, provider, "fallback", config.get("fallback", {}))
        
        # Store references
        setattr(self, f"{provider}_canvas", canvas)
        setattr(self, f"{provider}_scrollable_frame", scrollable_frame)
        
        # Schedule initial width configuration after widget is mapped
        def initial_config():
            canvas.update_idletasks()
            scrollable_frame.update_idletasks()
            canvas.event_generate('<Configure>')
            # Force canvas to be visible
            canvas.focus_set()
            canvas.event_generate('<Enter>')
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        # Multiple attempts to ensure display
        self.after(1, initial_config)   # Very immediate
        self.after(25, initial_config)
        self.after(50, initial_config)
        self.after(100, initial_config)
        self.after(200, initial_config) # Later fallback
    
    def create_model_section(self, parent, provider, model_type, config):
        """Create a model configuration section."""
        # Model section frame
        section_frame = tk.Frame(parent, bg="#212121", bd=1, relief="solid", highlightbackground="#555555")
        section_frame.pack(fill=tk.X, padx=10, pady=5)
        
        section_label = tk.Label(section_frame, text=f"{model_type.title()} Model", 
                               bg="#212121", fg="#ffffff", font=("Arial", 14, "bold"))
        section_label.pack(anchor="nw", padx=10, pady=(5, 0))
        
        content_frame = tk.Frame(section_frame, bg="#212121")
        content_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        row = 0
        
        # Model name
        tk.Label(content_frame, text="Model:", font=("Arial", 12, "bold"), bg="#212121", fg="#ffffff").grid(row=row, column=0, sticky="w", padx=5, pady=5)
        model_var = tk.StringVar(value=config.get("model", ""))
        model_entry = ttk.Entry(content_frame, textvariable=model_var, width=30, style='Borderless.TEntry')
        model_entry.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
        setattr(self, f"{provider}_{model_type}_model_var", model_var)
        row += 1
        
        # Parameters
        tk.Label(content_frame, text="Parameters:", font=("Arial", 12, "bold"), bg="#212121", fg="#ffffff").grid(row=row, column=0, sticky="nw", padx=5, pady=5)
        
        # Extract parameters from config (exclude model and prompt)
        parameters = {}
        for key, value in config.items():
            if key not in ["model", "prompt"]:
                parameters[key] = value
        
        parameters_json = json.dumps(parameters, indent=2)
        
        params_frame = tk.Frame(content_frame, bg="#212121")
        params_frame.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
        
        parameters_text = scrolledtext.ScrolledText(params_frame, width=50, height=6, wrap=tk.WORD,
                                                   bg="#3c3c3c", fg="#ffffff",
                                                   insertbackground="#ffffff",
                                                   selectbackground="#404040")
        parameters_text.pack(fill=tk.BOTH, expand=True)
        parameters_text.insert("1.0", parameters_json)
        setattr(self, f"{provider}_{model_type}_parameters_text", parameters_text)
        row += 1
        
        # Prompt
        tk.Label(content_frame, text="Prompt:", font=("Arial", 12, "bold"), bg="#212121", fg="#ffffff").grid(row=row, column=0, sticky="nw", padx=5, pady=5)
        
        prompt_frame = tk.Frame(content_frame, bg="#212121")
        prompt_frame.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
        
        prompt_text = scrolledtext.ScrolledText(prompt_frame, width=50, height=15, wrap=tk.WORD,
                                               bg="#3c3c3c", fg="#ffffff",
                                               insertbackground="#ffffff",
                                               selectbackground="#404040")
        prompt_text.pack(fill=tk.BOTH, expand=True)
        prompt_text.insert("1.0", config.get("prompt", ""))
        setattr(self, f"{provider}_{model_type}_prompt_text", prompt_text)
        row += 1
        
        # Configure grid weights
        content_frame.columnconfigure(1, weight=1)
    
    def create_general_settings(self, parent):
        """Create general settings widgets."""
        # Create a simple frame for general settings (no scrolling needed)
        settings_frame = ttk.Frame(parent)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Concurrent threads setting - use manual dark frame styling
        threads_frame = tk.Frame(settings_frame, bg="#212121", bd=1, relief="solid", highlightbackground="#555555")
        threads_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Manual label for threads frame
        threads_label = tk.Label(threads_frame, text="Processing Settings", 
                               bg="#212121", fg="#ffffff", font=("Arial", 14, "bold"))
        threads_label.pack(anchor="nw", padx=10, pady=(5, 0))
        
        threads_inner = tk.Frame(threads_frame, bg="#212121")
        threads_inner.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Label(threads_inner, text="Concurrent Threads:", bg="#212121", fg="#ffffff", font=("Arial", 14)).grid(row=0, column=0, sticky="w", padx=(0, 10))
        
        self.threads_var = tk.IntVar(value=self.general_settings.get("max_workers", 1))
        threads_spinbox = ttk.Spinbox(threads_inner, from_=1, to=10, width=10, textvariable=self.threads_var)
        threads_spinbox.grid(row=0, column=1, sticky="w")
        
        # Help text
        help_text = tk.Label(threads_inner, 
                           text="Number of concurrent threads for processing files.\n"
                                "Higher values may speed up processing but could hit API rate limits.\n"
                                "Recommended: 1-3 threads for most use cases.",
                           font=("Arial", 14),
                           fg="#ffffff",
                           bg="#212121",
                           justify="left")
        help_text.grid(row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))
        
        # Performance note - use manual dark frame styling
        perf_frame = tk.Frame(settings_frame, bg="#212121", bd=1, relief="solid", highlightbackground="#555555")
        perf_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Manual label for performance frame
        perf_label = tk.Label(perf_frame, text="Performance Notes", 
                            bg="#212121", fg="#ffffff", font=("Arial", 14, "bold"))
        perf_label.pack(anchor="nw", padx=10, pady=(5, 0))
        
        perf_inner = tk.Frame(perf_frame, bg="#212121")
        perf_inner.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        perf_text = tk.Label(perf_inner,
                           text="• 1 thread: Sequential processing (safest, slowest)\n"
                                "• 2-3 threads: Good balance of speed and reliability\n"
                                "• 4+ threads: Faster but may hit OpenAI rate limits\n",
                           font=("Arial", 14),
                           justify="left",
                           bg="#212121",
                           fg="#ffffff")
        perf_text.pack(anchor="w")

    def save_settings(self):
        """Save the current settings."""
        try:
            # Update provider configs
            for provider in ["openai", "anthropic", "openrouter", "google"]:
                if provider not in self.provider_configs:
                    self.provider_configs[provider] = {}
                
                # API key
                api_key_var = getattr(self, f"{provider}_api_key_var")
                self.provider_configs[provider]["api_key"] = api_key_var.get()
                
                # Primary and fallback configs
                for model_type in ["primary", "fallback"]:
                    if model_type not in self.provider_configs[provider]:
                        self.provider_configs[provider][model_type] = {}
                    
                    config = self.provider_configs[provider][model_type]
                    config.clear()
                    
                    # Model
                    model_var = getattr(self, f"{provider}_{model_type}_model_var")
                    config["model"] = model_var.get()
                    
                    # Prompt
                    prompt_text = getattr(self, f"{provider}_{model_type}_prompt_text")
                    config["prompt"] = prompt_text.get("1.0", tk.END).strip()
                    
                    # Parameters
                    parameters_text = getattr(self, f"{provider}_{model_type}_parameters_text")
                    parameters_str = parameters_text.get("1.0", tk.END).strip()
                    if parameters_str:
                        try:
                            parameters = json.loads(parameters_str)
                            config.update(parameters)
                        except json.JSONDecodeError as e:
                            messagebox.showerror("Invalid JSON", f"{provider.title()} {model_type} parameters contain invalid JSON: {e}")
                            return
            
            # Update general settings
            self.general_settings["max_workers"] = self.threads_var.get()
            
            self.result = {"provider_configs": self.provider_configs, "general_settings": self.general_settings}
            self.cancel()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error saving settings: {e}")
    
    def on_tab_changed(self, event):
        """Handle tab change event to refresh display."""
        # Get the currently selected tab
        selected_tab = self.notebook.select()
        tab_text = self.notebook.tab(selected_tab, "text").lower()
        
        # Force update for provider tabs that use canvas
        if tab_text in ["openai", "anthropic", "openrouter", "google"]:
            def force_canvas_display():
                if hasattr(self, f"{tab_text}_canvas") and hasattr(self, f"{tab_text}_scrollable_frame"):
                    canvas = getattr(self, f"{tab_text}_canvas")
                    scrollable_frame = getattr(self, f"{tab_text}_scrollable_frame")
                    
                    # Force the canvas to be visible and mapped
                    canvas.update_idletasks()
                    scrollable_frame.update_idletasks()
                    
                    # Trigger configure events
                    canvas.event_generate('<Configure>')
                    
                    # Force focus and mapping
                    canvas.focus_set()
                    
                    # Programmatically trigger mouse enter to force display
                    canvas.event_generate('<Enter>')
                    
                    # Force scroll region update
                    canvas.configure(scrollregion=canvas.bbox("all"))
                    
                    # Additional forced update
                    self.update()
            
            # Immediate update
            self.update_idletasks()
            force_canvas_display()
            
            # Also schedule a delayed update to ensure it takes effect
            self.after(10, force_canvas_display)
            self.after(50, force_canvas_display)
    
    def force_initial_update(self):
        """Force initial update of all tabs to ensure proper display."""
        # Update the dialog and all its children
        self.update_idletasks()
        
        # Force update for all provider canvases
        for provider in ["openai", "anthropic", "openrouter", "google"]:
            if hasattr(self, f"{provider}_canvas"):
                canvas = getattr(self, f"{provider}_canvas")
                canvas.update_idletasks()
                # Force width recalculation
                self.after(10, lambda c=canvas: c.event_generate('<Configure>'))
    
    def force_canvas_layout(self):
        """Force all canvas widgets to recalculate their layout."""
        for provider in ["openai", "anthropic", "openrouter", "google"]:
            if hasattr(self, f"{provider}_canvas"):
                canvas = getattr(self, f"{provider}_canvas")
                canvas.update_idletasks()
                canvas.event_generate('<Configure>')
                # Ensure scrollregion is updated too
                canvas.configure(scrollregion=canvas.bbox("all"))
    
    def reset_defaults(self):
        """Reset to default settings."""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to defaults?"):
            # Create default provider configs
            default_configs = {}
            for provider in ["openai", "anthropic", "openrouter", "google"]:
                temp_ocr = HandwritingOCR("dummy_key", provider=provider)
                default_configs[provider] = {
                    "api_key": "",
                    "primary": temp_ocr.transcription_config["primary"].copy(),
                    "fallback": temp_ocr.transcription_config["fallback"].copy()
                }
            
            # Set result to indicate defaults should be applied
            self.result = {"provider_configs": default_configs, "general_settings": {"max_workers": 1}}
            self.cancel()


class OCRProgressDialog(BaseDialog):
    """Dialog showing OCR processing progress."""
    
    def __init__(self, parent, total_files: int, log_queue=None):
        super().__init__(parent, "Processing Files", min_width=500, min_height=250, resizable=(False, False))
        
        self.total_files = total_files
        self.current_file = 0
        self.cancelled = False
        self.log_queue = log_queue
        self.log_viewer = None
        
        # Prevent closing with default cancel
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        
        self.create_widgets()
        
    def create_widgets(self):
        """Create progress dialog widgets."""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Preparing to process files...", font=("Arial", 16))
        self.status_label.pack(pady=(0, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        # File counter
        self.counter_label = ttk.Label(main_frame, text=f"0 images processed of {self.total_files}", font=("Arial", 16))
        self.counter_label.pack(pady=(0, 10))
        
        # Current file label
        self.current_file_label = ttk.Label(main_frame, text="", wraplength=450, font=("Arial", 16))
        self.current_file_label.pack(pady=(0, 10))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        # View Logs button (only show if log_queue is available)
        if self.log_queue:
            ttk.Button(button_frame, text="View Logs", command=self.show_logs, style='Rounded.TButton').pack(side=tk.LEFT, padx=(0, 10))
        
        # Cancel button
        ttk.Button(button_frame, text="Cancel", command=self.cancel, style='Rounded.TButton').pack(side=tk.RIGHT)
        
    def update_progress(self, current_file: int, filename: str, status: str):
        """Update progress display."""
        self.current_file = current_file
        progress_percent = (current_file / self.total_files) * 100
        
        self.progress_var.set(progress_percent)
        self.counter_label.config(text=f"{current_file} images processed of {self.total_files}")
        self.current_file_label.config(text=f"Current: {filename}")
        self.status_label.config(text=status)
        
        self.update()
        
    def on_log_viewer_closed(self):
        """Callback for when the log viewer is closed."""
        self.log_viewer = None
        
    def show_logs(self):
        """Show the log viewer dialog."""
        if self.log_queue:
            if self.log_viewer is None:
                # Create a new log viewer if one isn't active
                self.log_viewer = LogViewerDialog(self, self.log_queue, on_close=self.on_log_viewer_closed)
            else:
                try:
                    # If the window exists, bring it to the front
                    self.log_viewer.lift()
                    self.log_viewer.grab_set()
                except tk.TclError:
                    # Failsafe: if the window was destroyed unexpectedly
                    self.log_viewer = LogViewerDialog(self, self.log_queue, on_close=self.on_log_viewer_closed)
    
    def cancel(self):
        """Handle cancel request."""
        if messagebox.askyesno("Cancel Processing", "Are you sure you want to cancel processing?"):
            self.cancelled = True
            # Close log viewer if open
            if self.log_viewer:
                self.log_viewer.cancel()
            super().cancel()
    
    def close(self):
        """Close the dialog."""
        # Close log viewer if open
        if self.log_viewer:
            self.log_viewer.cancel()
        super().cancel()


class FileProcessor:
    """Handles the backend file processing logic."""

    def __init__(self, ocr_processor, file_paths, max_workers, logger, progress_callback):
        self.ocr_processor = ocr_processor
        self.file_paths = file_paths
        self.max_workers = max_workers
        self.logger = logger
        self.progress_callback = progress_callback
        self.cancelled = False
        self.processed_count = 0

    def cancel(self):
        """Cancel the processing task."""
        self.cancelled = True

    def _process_single_file(self, file_path, page_number):
        """Processes a single file and updates progress."""
        if self.cancelled:
            raise Exception("Processing cancelled by user")

        filename = os.path.basename(file_path)

        # Update progress dialog - starting file
        self.progress_callback("start", self.processed_count, filename)

        try:
            # Transcribe the image using the original file path
            self.logger.info(f"Starting transcription for {filename}")
            transcription = self.ocr_processor.transcribe_image(file_path)
            self.logger.info(f"Transcription completed for {filename}")

            # Create individual PDF for this image in the source directory
            pdf_filename = f"{Path(file_path).stem}.pdf"
            self.logger.info(f"Creating PDF for {filename}")
            pdf_path = self.ocr_processor.create_individual_pdf(file_path, transcription, pdf_filename)
            self.logger.info(f"PDF created: {pdf_filename}")

            self.processed_count += 1
            self.progress_callback("complete", self.processed_count, filename)

            return {
                "image_path": file_path, "filename": filename, "transcription": transcription,
                "pdf_path": pdf_path, "page_number": page_number, "status": "success"
            }

        except Exception as e:
            self.logger.error(f"Error processing {filename}: {str(e)}")
            self.processed_count += 1
            self.progress_callback("error", self.processed_count, filename)

            return {
                "image_path": file_path, "filename": filename, "transcription": f"[Error: {str(e)}]",
                "pdf_path": None, "page_number": page_number, "status": "error", "error": str(e)
            }

    def run(self):
        """Run the file processing task."""
        self.logger.info(f"Starting batch processing of {len(self.file_paths)} files with {self.max_workers} threads")
        results = []
        pdf_paths = []

        if self.max_workers == 1:
            self.logger.info("Processing files sequentially...")
            for i, file_path in enumerate(self.file_paths, 1):
                if self.cancelled:
                    self.logger.info("Processing cancelled by user")
                    break
                result = self._process_single_file(file_path, i)
                results.append(result)
        else:
            self.logger.info(f"Processing files with {self.max_workers} concurrent threads...")
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_info = {executor.submit(self._process_single_file, fp, i): (fp, i) for i, fp in enumerate(self.file_paths, 1)}

                completed_results = []
                for future in as_completed(future_to_info):
                    if self.cancelled:
                        self.logger.info("Processing cancelled by user")
                        # Cancel remaining futures
                        for f in future_to_info:
                            f.cancel()
                        break
                    result = future.result()
                    completed_results.append(result)

                # Sort results by page number to maintain order
                results = sorted(completed_results, key=lambda x: x["page_number"])

        pdf_paths = [r["pdf_path"] for r in results if r and r.get("pdf_path")]
        return results, pdf_paths


class OCRApp:
    """Main OCR GUI Application."""
    
    def __init__(self):
        self.root = tkdnd.Tk()
        self.root.title("Genealogy Assistant AI HTR Tool")
        self.root.geometry("800x750")
        
        # Configure dark theme for consistent appearance across platforms
        self.configure_theme()
        
        # Set up logging system
        self.setup_logging()
        
        # Initialize OCR processor (will be created when provider and API key are set)
        self.ocr_processor = None
        self.selected_provider = "openai"  # Default provider
        self.provider_configs = {
            "openai": {"api_key": "", "primary": {}, "fallback": {}},
            "anthropic": {"api_key": "", "primary": {}, "fallback": {}},
            "openrouter": {"api_key": "", "primary": {}, "fallback": {}},
            "google": {"api_key": "", "primary": {}, "fallback": {}}
        }
        self.general_settings = {"max_workers": 1}  # Default general settings
        
        # Initialize default configs for all providers
        self._initialize_default_configs()
        
        # Load settings using platform-appropriate path
        self.settings_file = Path(get_settings_path())
        self.load_settings()
        
        self.create_widgets()
        self.setup_drag_drop()
        
        # Update GUI after loading settings
        self.update_gui_after_loading()
        
                # Center window
        self.center_window()
    
    def _initialize_default_configs(self):
        """Initialize default configurations for all providers."""
        for provider in ["openai", "anthropic", "openrouter", "google"]:
            if not self.provider_configs[provider].get("primary") or not self.provider_configs[provider].get("fallback"):
                try:
                    temp_ocr = HandwritingOCR("dummy_key", provider=provider)
                    if not self.provider_configs[provider].get("primary"):
                        self.provider_configs[provider]["primary"] = temp_ocr.transcription_config["primary"].copy()
                    if not self.provider_configs[provider].get("fallback"):
                        self.provider_configs[provider]["fallback"] = temp_ocr.transcription_config["fallback"].copy()
                except Exception:
                    # Use basic defaults if can't create temp OCR
                    if not self.provider_configs[provider].get("primary"):
                        self.provider_configs[provider]["primary"] = {"model": "", "prompt": ""}
                    if not self.provider_configs[provider].get("fallback"):
                        self.provider_configs[provider]["fallback"] = {"model": "", "prompt": ""}
 
    def setup_logging(self):
        """Set up the logging system for real-time log viewing."""
        # Create a queue for log messages
        self.log_queue = queue.Queue()
        
        # Create and configure the custom log handler
        self.log_handler = LogHandler(self.log_queue)
        self.log_handler.setLevel(logging.INFO)
        
        # Create a logger for the application
        self.logger = logging.getLogger('genea_htr')
        self.logger.setLevel(logging.INFO)
        
        # Clear any existing handlers to prevent duplicates
        self.logger.handlers.clear()
        
        # Add our custom handler
        self.logger.addHandler(self.log_handler)
        
        # Prevent propagation to root logger to avoid duplicates
        self.logger.propagate = False
        
        # Log the application start
        self.logger.info("Application started")
    
    def configure_theme(self):
        """Configure dark theme for consistent appearance across platforms."""
        try:
            # Configure ttk style for dark theme
            style = ttk.Style()
            
            # Set dark theme colors - more consistent with the original design
            dark_bg = "#2b2b2b"
            dark_fg = "#ffffff"
            dark_select_bg = "#404040"
            dark_field_bg = "#3c3c3c"
            dark_button_bg = "#4a4a4a"
            dark_button_hover = "#5a5a5a"
            dark_button_pressed = "#6a6a6a"
            dark_border = "#555555"
            
            # Configure the root window
            self.root.configure(bg=dark_bg)
            
            # Configure ttk styles for dark theme
            style.theme_use('clam')  # Use clam theme as base for better customization
            
            # Configure Frame style
            style.configure('TFrame', background=dark_bg, borderwidth=0)
            
            # Configure LabelFrame with more aggressive dark styling
            style.configure('TLabelFrame', 
                          background=dark_bg, 
                          foreground=dark_fg,
                          borderwidth=1,
                          relief='solid',
                          bordercolor=dark_border,
                          lightcolor=dark_bg,
                          darkcolor=dark_bg,
                          focuscolor=dark_bg)
            style.configure('TLabelFrame.Label', 
                          background=dark_bg, 
                          foreground=dark_fg,
                          font=('Arial', 10, 'bold'))
            
            # Map LabelFrame to ensure dark background in all states
            style.map('TLabelFrame',
                     background=[('active', dark_bg), ('!active', dark_bg), ('focus', dark_bg), ('!focus', dark_bg)],
                     lightcolor=[('active', dark_bg), ('!active', dark_bg), ('focus', dark_bg), ('!focus', dark_bg)],
                     darkcolor=[('active', dark_bg), ('!active', dark_bg), ('focus', dark_bg), ('!focus', dark_bg)],
                     focuscolor=[('active', dark_bg), ('!active', dark_bg), ('focus', dark_bg), ('!focus', dark_bg)])
            
            # Create a custom dark LabelFrame style
            style.configure('Dark.TLabelFrame', 
                          background=dark_bg, 
                          foreground=dark_fg,
                          borderwidth=1,
                          relief='solid',
                          bordercolor=dark_border,
                          lightcolor=dark_bg,
                          darkcolor=dark_bg,
                          focuscolor=dark_bg)
            style.configure('Dark.TLabelFrame.Label', 
                          background=dark_bg, 
                          foreground=dark_fg,
                          font=('Arial', 14, 'bold'))
            style.map('Dark.TLabelFrame',
                     background=[('active', dark_bg), ('!active', dark_bg), ('focus', dark_bg), ('!focus', dark_bg)],
                     lightcolor=[('active', dark_bg), ('!active', dark_bg), ('focus', dark_bg), ('!focus', dark_bg)],
                     darkcolor=[('active', dark_bg), ('!active', dark_bg), ('focus', dark_bg), ('!focus', dark_bg)],
                     focuscolor=[('active', dark_bg), ('!active', dark_bg), ('focus', dark_bg), ('!focus', dark_bg)])
            
            # Configure Label style
            style.configure('TLabel', 
                          background=dark_bg, 
                          foreground=dark_fg,
                          font=('Arial', 10))
            
            # Configure Entry style with rounded appearance
            style.configure('TEntry', 
                          background=dark_field_bg, 
                          foreground=dark_fg,
                          fieldbackground=dark_field_bg,
                          bordercolor=dark_border,
                          insertcolor=dark_fg,
                          borderwidth=1,
                          relief='solid')
            style.map('TEntry',
                     focuscolor=[('!focus', dark_border)],
                     bordercolor=[('focus', '#7a7a7a')])
            
            # Create a borderless style for the API key entry to avoid double borders
            style.configure('Borderless.TEntry',
                            background='#212121',
                            fieldbackground=dark_field_bg,
                            foreground=dark_fg,
                            insertcolor=dark_fg,
                            borderwidth=0)
            
            # Configure Button style for squared buttons
            style.configure('Rounded.TButton',
                          background=dark_button_bg,
                          foreground=dark_fg,
                          bordercolor=dark_border,
                          focuscolor='none',
                          borderwidth=1,
                          relief='solid',
                          padding=(12, 6),
                          font=('Arial', 14, 'bold'))
            style.map('Rounded.TButton',
                     background=[('active', dark_button_hover), ('pressed', dark_button_pressed)],
                     bordercolor=[('focus', dark_border), ('active', dark_border)])
            
            # Create a green button style for the Process Files button
            style.configure('Green.TButton',
                          background='#109322',
                          foreground='#ffffff',
                          bordercolor='#109322',
                          focuscolor='none',
                          borderwidth=1,
                          relief='solid',
                          padding=(12, 6),
                          font=('Arial', 18, 'bold'))
            style.map('Green.TButton',
                     background=[('active', '#0d7a1c'), ('pressed', '#0a5e16')],
                     bordercolor=[('focus', '#109322'), ('active', '#0d7a1c')],
                     foreground=[('disabled', '#92ba98')])
            
            # Configure Notebook style
            style.configure('TNotebook', 
                          background=dark_bg, 
                          bordercolor=dark_border,
                          tabmargins=[2, 5, 2, 0])
            style.configure('TNotebook.Tab',
                          background=dark_button_bg,
                          foreground=dark_fg,
                          padding=[12, 8],
                          borderwidth=1,
                          font=("Arial", 14, "bold"))
            style.map('TNotebook.Tab',
                     background=[('selected', dark_select_bg), ('active', dark_button_hover)],
                     bordercolor=[('selected', dark_border), ('active', dark_border)],
                     padding=[('selected', [12, 8]), ('!selected', [12, 8])],  # Ensure consistent padding
                     borderwidth=[('selected', 1), ('!selected', 1)])
            
            # Configure Progressbar style
            style.configure('TProgressbar',
                          background='#4CAF50',
                          troughcolor=dark_field_bg,
                          bordercolor=dark_border,
                          borderwidth=1,
                          relief='solid')
            
            # Configure Scrollbar style
            style.configure('TScrollbar',
                          background=dark_button_bg,
                          troughcolor=dark_field_bg,
                          bordercolor=dark_border,
                          arrowcolor=dark_fg,
                          borderwidth=1)
            style.map('TScrollbar',
                     background=[('active', dark_button_hover)])
            
            # Configure Checkbutton style
            style.configure('TCheckbutton',
                          background=dark_bg,
                          foreground=dark_fg,
                          font=('Arial', 14),
                          padding=5)
            style.map('TCheckbutton',
                     background=[('active', dark_bg)],
                     foreground=[('disabled', '#aaaaaa')])
            
            # Configure Spinbox style
            style.configure('TSpinbox',
                          background=dark_field_bg,
                          foreground=dark_fg,
                          fieldbackground=dark_field_bg,
                          bordercolor=dark_border,
                          arrowcolor=dark_fg,
                          borderwidth=1,
                          relief='solid')
            
        except Exception as e:
            print(f"Error configuring theme: {e}")
            # Continue without custom theme if there's an error
        
    def create_header(self):
        """Create the header with clickable image."""
        try:
            # Load and resize the header image using resource path function
            header_path = get_resource_path("htr-app-header.png")
            if os.path.exists(header_path):
                # Open the image
                pil_image = Image.open(header_path)
                
                # Calculate the scaling to fit the window width while maintaining aspect ratio,
                # accounting for Windows DPI scaling.
                base_width = 800  # The application's logical width
                window_width = base_width

                if sys.platform == 'win32':
                    try:
                        from ctypes import windll
                        # Get the system DPI and calculate scaling factor. 96 is the default DPI.
                        # This call is available on Windows 10, v1607+
                        dpi = windll.user32.GetDpiForSystem()
                    except (AttributeError, OSError):
                        # Fallback for older Windows versions
                        try:
                            from ctypes import windll
                            dc = windll.user32.GetDC(0)
                            # LOGPIXELSX corresponds to the horizontal DPI
                            dpi = windll.gdi32.GetDeviceCaps(dc, 88)
                            windll.user32.ReleaseDC(0, dc)
                        except Exception:
                            dpi = 96  # Default DPI

                    scaling_factor = dpi / 96.0
                    window_width = int(base_width * scaling_factor)

                # Calculate the scaling to fit the window width (800px) while maintaining aspect ratio
                original_width, original_height = pil_image.size
                scale_factor = window_width / original_width
                new_width = window_width
                new_height = int(original_height * scale_factor)
                
                # Resize the image
                pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert to PhotoImage
                self.header_image = ImageTk.PhotoImage(pil_image)
                
                # Create header frame with no background and tight packing
                header_frame = tk.Frame(self.root, bg="black", bd=0, highlightthickness=0)
                header_frame.pack(fill=tk.X, padx=0, pady=0, ipadx=0, ipady=0)
                
                # Create clickable header label with no padding
                header_label = tk.Label(
                    header_frame,
                    image=self.header_image,
                    cursor="hand2",
                    bg="black",
                    bd=0,
                    highlightthickness=0
                )
                header_label.pack(fill=tk.X, padx=0, pady=0, ipadx=0, ipady=0)
                
                # Bind click event to open website
                header_label.bind("<Button-1>", self.open_genea_website)
                
                # Make the frame also clickable
                header_frame.bind("<Button-1>", self.open_genea_website)
                header_frame.config(cursor="hand2")
                
                # Add hover effects with pointer cursor
                def on_enter(event):
                    event.widget.config(cursor="hand2")
                
                def on_leave(event):
                    event.widget.config(cursor="hand2")
                
                header_label.bind("<Enter>", on_enter)
                header_label.bind("<Leave>", on_leave)
                header_frame.bind("<Enter>", on_enter)
                header_frame.bind("<Leave>", on_leave)
                
        except Exception as e:
            print(f"Error loading header image: {e}")

    def open_genea_website(self, event=None):
        """Open the Genea website in the default browser."""
        webbrowser.open("https://chromewebstore.google.com/detail/genealogy-assistant/knnjkkdihbjonnkmajijmnfblpbopapk")

    def center_window(self):
        """Center the main window on screen."""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.root.winfo_screenheight() // 2) - (800 // 2)
        self.root.geometry(f"800x800+{x}+{y}")
        
    def create_widgets(self):
        """Create the main application widgets."""
        self.create_header()
        
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self._create_api_section(main_frame)
        self._create_settings_button_section(main_frame)
        self._create_dnd_section(main_frame)
        self._create_file_list_section(main_frame)
        self._create_process_button(main_frame)
        self._create_status_bar(main_frame)
        
        # File list to store file paths
        self.file_paths = []

    def _create_section(self, parent, text, inner_frame_pack_options=None):
        """Helper to create a styled section frame."""
        if inner_frame_pack_options is None:
            inner_frame_pack_options = {"fill": tk.X, "padx": 10, "pady": (0, 10)}

        outer_frame = tk.Frame(parent, bg="#212121", bd=1, relief="solid", highlightbackground="#555555")
        
        label = tk.Label(outer_frame, text=text, 
                           bg="#212121", fg="#ffffff", font=("Arial", 14, "bold"))
        label.pack(anchor="nw", padx=10, pady=(5, 0))
        
        inner_frame = tk.Frame(outer_frame, bg="#212121")
        inner_frame.pack(**inner_frame_pack_options)
        
        return outer_frame, inner_frame

    def _create_api_section(self, parent):
        """Create the provider selection section."""
        provider_outer_frame, provider_inner_frame = self._create_section(parent, "AI Provider Configuration")
        provider_outer_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create a grid layout for better spacing
        provider_inner_frame.grid_columnconfigure(1, weight=1)
        provider_inner_frame.grid_columnconfigure(2, weight=2)
        
        tk.Label(provider_inner_frame, text="Provider:", bg="#212121", fg="#ffffff", font=("Arial", 14, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        
        self.provider_var = tk.StringVar(value=self.selected_provider)
        provider_combo = ttk.Combobox(provider_inner_frame, textvariable=self.provider_var, 
                                    values=["OpenAI", "Anthropic", "OpenRouter", "Google"], 
                                    state="readonly", width=25, font=("Arial", 14, "bold"))
        provider_combo.grid(row=0, column=1, sticky="ew", padx=(0, 15), pady=5)
        provider_combo.bind("<<ComboboxSelected>>", self.on_provider_changed)
        
        # Status label
        self.provider_status_label = tk.Label(provider_inner_frame, text="", bg="#212121", fg="#ffffff", font=("Arial", 12))
        self.provider_status_label.grid(row=0, column=2, sticky="w", pady=5)

    def _create_settings_button_section(self, parent):
        """Create the 'Edit Settings' button."""
        settings_frame = ttk.Frame(parent)
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(settings_frame, text="Edit Settings", command=self.open_settings, style='Rounded.TButton').pack(side=tk.RIGHT, padx=(0, 10))

    def _create_dnd_section(self, parent):
        """Create the drag-and-drop section."""
        drop_pack_options = {"fill": tk.BOTH, "expand": True, "padx": 20, "pady": (0, 20)}
        drop_outer_frame, drop_content = self._create_section(parent, "Drag & Drop Files Here", drop_pack_options)
        drop_outer_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.drop_frame = drop_outer_frame

        drop_container = tk.Frame(drop_content, bg="#212121")
        drop_container.pack(expand=True)

        self.drop_icon = tk.Label(drop_container, text="📁", font=("Arial", 64), anchor="center", bg="#212121", fg="#ffffff")
        self.drop_icon.pack(pady=(0, 10))

        self.drop_label = tk.Label(drop_container, text="Drag image/PDF files here\nor click to browse", font=("Arial", 16), anchor="center", justify="center", bg="#212121", fg="#ffffff")
        self.drop_label.pack()

        for widget in [self.drop_icon, self.drop_label, drop_container, self.drop_frame]:
            widget.bind("<Button-1>", self.browse_files)
    
    def _create_file_list_section(self, parent):
        """Create the file list display section."""
        list_outer_frame, list_inner_frame = self._create_section(parent, "Selected Files", {"fill": tk.X, "padx": 10, "pady": (0, 10)})
        list_outer_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.file_listbox = tk.Listbox(list_inner_frame, height=6,
                                     bg="#3c3c3c", fg="#ffffff",
                                     selectbackground="#404040", selectforeground="#ffffff",
                                     borderwidth=1, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_inner_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        file_buttons_frame = tk.Frame(list_outer_frame, bg="#212121")
        file_buttons_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(file_buttons_frame, text="Clear All", command=self.clear_files, style='Rounded.TButton').pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(file_buttons_frame, text="Remove Selected", command=self.remove_selected, style='Rounded.TButton').pack(side=tk.RIGHT)

    def _create_process_button(self, parent):
        """Create the main 'Process Files' button."""
        self.process_button = ttk.Button(parent, text="Process Files", command=self.process_files, state="disabled", style='Green.TButton')
        self.process_button.pack(pady=(0, 10))

    def _create_status_bar(self, parent):
        """Create the status bar at the bottom."""
        self.status_var = tk.StringVar(value=f"Ready - Configure AI provider in Settings | v{VERSION}")
        status_bar = ttk.Entry(parent, textvariable=self.status_var, state="readonly")
        status_bar.pack(fill=tk.X, pady=(5, 0))

    def setup_drag_drop(self):
        """Setup drag and drop functionality."""
        # Register the drop target
        self.drop_frame.drop_target_register(tkdnd.DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self.on_drop)
        
        # Also register the icon and label inside
        self.drop_icon.drop_target_register(tkdnd.DND_FILES)
        self.drop_icon.dnd_bind('<<Drop>>', self.on_drop)
        self.drop_label.drop_target_register(tkdnd.DND_FILES)
        self.drop_label.dnd_bind('<<Drop>>', self.on_drop)
        
    def on_drop(self, event):
        """Handle file drop event."""
        files = self.root.tk.splitlist(event.data)
        self.add_files(files)
        
    def browse_files(self, event=None):
        """Open file browser to select files."""
        files = filedialog.askopenfilenames(
            title="Select image and PDF files",
            filetypes=[
                ("All supported", "*.jpg *.jpeg *.png *.pdf *.JPG *.JPEG *.PNG *.PDF"),
                ("Image files", "*.jpg *.jpeg *.png *.JPG *.JPEG *.PNG"),
                ("PDF files", "*.pdf *.PDF"),
                ("All files", "*.*")
            ]
        )
        if files:
            self.add_files(files)
            
    def add_files(self, files):
        """Add files to the processing list."""
        added_count = 0
        for file_path in files:
            # Check if it's a supported file type
            if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.pdf')):
                if file_path not in self.file_paths:
                    self.file_paths.append(file_path)
                    self.file_listbox.insert(tk.END, os.path.basename(file_path))
                    added_count += 1
            else:
                messagebox.showwarning("Invalid File", f"Skipping unsupported file: {os.path.basename(file_path)} (only JPEG, PNG, and PDF files are supported)")
        
        if added_count > 0:
            self.status_var.set(f"Added {added_count} file(s). Total: {len(self.file_paths)} files")
            self.update_process_button()
        
    def remove_selected(self):
        """Remove selected files from the list."""
        selection = self.file_listbox.curselection()
        if selection:
            # Remove in reverse order to maintain indices
            for index in reversed(selection):
                self.file_listbox.delete(index)
                del self.file_paths[index]
            self.status_var.set(f"Removed selected files. Total: {len(self.file_paths)} files")
            self.update_process_button()
        
    def clear_files(self):
        """Clear all files from the list."""
        if self.file_paths and messagebox.askyesno("Clear Files", "Remove all files from the list?", parent=self.root):
            self.file_listbox.delete(0, tk.END)
            self.file_paths.clear()
            self.status_var.set("All files cleared")
            self.update_process_button()
            
    def update_process_button(self):
        """Update the process button state."""
        if self.file_paths and self.ocr_processor:
            self.process_button.config(state="normal")
        else:
            self.process_button.config(state="disabled")
    
    def on_provider_changed(self, event=None):
        """Handle provider selection change."""
        # Convert display name to internal name
        display_to_internal = {"OpenAI": "openai", "Anthropic": "anthropic", "OpenRouter": "openrouter", "Google": "google"}
        self.selected_provider = display_to_internal.get(self.provider_var.get(), self.provider_var.get().lower())
        self.update_provider_status()
        self.try_create_ocr_processor()
        self.update_process_button()
        self.save_settings()
    
    def update_provider_status(self):
        """Update the provider status display."""
        provider_config = self.provider_configs.get(self.selected_provider, {})
        api_key = provider_config.get("api_key", "")
        
        # Proper display names for providers
        provider_names = {"openai": "OpenAI", "anthropic": "Anthropic", "openrouter": "OpenRouter", "google": "Google"}
        display_name = provider_names.get(self.selected_provider, self.selected_provider.title())
        
        if api_key:
            self.provider_status_label.config(text=f"✓ {display_name} API key configured", fg="#00ff00")
        else:
            self.provider_status_label.config(text=f"⚠ No {display_name} API key set - Configure in Settings", fg="#ffaa00")
    
    def try_create_ocr_processor(self):
        """Try to create OCR processor with current provider and API key."""
        provider_config = self.provider_configs.get(self.selected_provider, {})
        api_key = provider_config.get("api_key", "")
        
        if not api_key:
            self.ocr_processor = None
            return False
            
        try:
            max_workers = self.general_settings.get("max_workers", 1)
            self.ocr_processor = HandwritingOCR(api_key, provider=self.selected_provider, max_workers=max_workers)
            
            # Update transcription config with saved settings
            if "primary" in provider_config and "fallback" in provider_config:
                self.ocr_processor.transcription_config = {
                    "primary": provider_config["primary"].copy(),
                    "fallback": provider_config["fallback"].copy()
                }
            
            self.status_var.set(f"{self.selected_provider.title()} provider ready - Ready to process files | v{VERSION}")
            return True
        except Exception as e:
            self.ocr_processor = None
            self.status_var.set(f"Error with {self.selected_provider.title()} provider: {str(e)} | v{VERSION}")
            return False
            
    def open_settings(self):
        """Open the settings dialog."""
        dialog = SettingsDialog(self.root, self.provider_configs, self.general_settings)
        self.root.wait_window(dialog)
        
        if dialog.result:
            self.provider_configs = dialog.result["provider_configs"]
            self.general_settings = dialog.result["general_settings"]
            
            # Update provider status and try to recreate OCR processor
            self.update_provider_status()
            self.try_create_ocr_processor()
            self.update_process_button()
            
            self.save_settings()
            self.status_var.set(f"Settings updated | v{VERSION}")
            
    def process_files(self):
        """Process the selected files."""
        if not self.file_paths:
            messagebox.showwarning("No Files", "Please add some files to process", parent=self.root)
            return
            
        if not self.ocr_processor:
            messagebox.showerror("No API Key", "Please configure your AI provider API key in Settings first", parent=self.root)
            return
        
        # Check if we have PDF files and PyMuPDF is available
        pdf_files = [f for f in self.file_paths if f.lower().endswith('.pdf')]
        if pdf_files:
            try:
                import fitz  # PyMuPDF
            except ImportError:
                messagebox.showerror("Missing Dependency", 
                                   "PDF processing requires PyMuPDF. Please install it with:\n\npip install PyMuPDF", 
                                   parent=self.root)
                return
            
        progress_dialog = OCRProgressDialog(self.root, len(self.file_paths), self.log_queue)
        
        def progress_callback(status, current_file, filename):
            """Callback to update the progress dialog from the processing thread."""
            if progress_dialog.cancelled:
                return

            def update_ui():
                if progress_dialog.cancelled:
                    return
                
                status_map = {
                    "start": f"Processing {filename}...",
                    "complete": f"Completed {filename}",
                    "error": f"Error processing {filename}"
                }
                progress_dialog.update_progress(
                    current_file=current_file,
                    filename=filename,
                    status=status_map.get(status, "...")
                )
            self.root.after(0, update_ui)

        def process_thread():
            """The thread that runs the file processing."""
            max_workers = self.general_settings.get("max_workers", 1)
            processor = FileProcessor(self.ocr_processor, self.file_paths, max_workers, self.logger, progress_callback)
            
            # This makes the processor aware of the dialog's cancellation state
            def check_cancellation():
                if progress_dialog.cancelled:
                    processor.cancel()
                if not processor.cancelled:
                    self.root.after(100, check_cancellation)
            self.root.after(100, check_cancellation)

            try:
                results, pdf_paths = processor.run()
                
                def finish_processing():
                    try:
                        progress_dialog.close()
                    except tk.TclError:
                        pass  # Dialog might already be closed
                    
                    if not progress_dialog.cancelled:
                        if results:
                            self.show_results(results, pdf_paths)
                        else:
                            self.status_var.set("No files were processed.")
                    else:
                        self.status_var.set("Processing cancelled")
                
                self.root.after(0, finish_processing)
                    
            except Exception as e:
                def handle_error():
                    try:
                        progress_dialog.close()
                    except tk.TclError:
                        pass
                    
                    if "cancelled by user" not in str(e):
                        messagebox.showerror("Processing Error", f"An unexpected error occurred: {e}", parent=self.root)
                        self.status_var.set("Processing failed")
                    else:
                        self.status_var.set("Processing cancelled")
                
                self.root.after(0, handle_error)

        threading.Thread(target=process_thread, daemon=True).start()
        
    def show_results(self, results, pdf_paths):
        """Show processing results."""
        if results:
            successful_results = [r for r in results if r["status"] == "success"]
            failed_results = [r for r in results if r["status"] == "error"]
            
            message = f"Processing completed!\n\n"
            message += f"Successfully processed: {len(successful_results)} files\n"
            if failed_results:
                message += f"Failed to process: {len(failed_results)} files\n"
            
            if pdf_paths:
                message += f"\nPDFs saved to: {os.path.dirname(pdf_paths[0])}"
                message += f"\n\nWould you like to open the output folder?"
                
                # Ask if user wants to open the output folder
                if messagebox.askyesno("Processing Complete", message, parent=self.root):
                    import subprocess
                    import platform
                    
                    folder_path = os.path.dirname(pdf_paths[0])
                    if platform.system() == "Darwin":  # macOS
                        subprocess.run(["open", folder_path])
                    elif platform.system() == "Windows":
                        subprocess.run(["explorer", folder_path])
                    else:  # Linux
                        subprocess.run(["xdg-open", folder_path])
            else:
                message += f"\n\nNo PDFs were created due to processing errors."
                messagebox.showinfo("Processing Complete", message, parent=self.root)
            
            self.status_var.set(f"Processing complete - {len(successful_results)} successful, {len(failed_results)} failed")
        else:
            messagebox.showwarning("No Results", "No files were processed", parent=self.root)
            
    def update_gui_after_loading(self):
        """Update GUI elements after loading settings."""
        # Update the provider selection
        if hasattr(self, 'provider_var'):
            # Convert internal name to display name
            internal_to_display = {"openai": "OpenAI", "anthropic": "Anthropic", "openrouter": "OpenRouter", "google": "Google"}
            display_name = internal_to_display.get(self.selected_provider, self.selected_provider.title())
            self.provider_var.set(display_name)
            
        # Update provider status and try to create OCR processor
        if hasattr(self, 'provider_status_label'):
            self.update_provider_status()
            self.try_create_ocr_processor()
            
        # Update status based on whether we have a valid OCR processor
        if hasattr(self, 'status_var'):
            if self.ocr_processor:
                self.status_var.set(f"{self.selected_provider.title()} provider ready - Ready to process files | v{VERSION}")
            else:
                self.status_var.set(f"Ready - Configure API key in Settings | v{VERSION}")
                
        # Update process button state
        self.update_process_button()
            
    def load_settings(self):
        """Load settings from file."""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    
                    # Load provider configs
                    self.provider_configs = settings.get("provider_configs", {
                        "openai": {"api_key": "", "primary": {}, "fallback": {}},
                        "anthropic": {"api_key": "", "primary": {}, "fallback": {}},
                        "openrouter": {"api_key": "", "primary": {}, "fallback": {}},
                        "google": {"api_key": "", "primary": {}, "fallback": {}}
                    })
                    
                    # Load selected provider
                    self.selected_provider = settings.get("selected_provider", "openai")
                    
                    # Load general settings
                    self.general_settings = settings.get("general_settings", {"max_workers": 1})
                    
                    # Ensure all providers have default configs if missing
                    for provider in ["openai", "anthropic", "openrouter", "google"]:
                        if provider not in self.provider_configs:
                            self.provider_configs[provider] = {"api_key": "", "primary": {}, "fallback": {}}
                    
                    # Load default provider configs if missing primary/fallback
                    for provider in ["openai", "anthropic", "openrouter", "google"]:
                        provider_config = self.provider_configs[provider]
                        if not provider_config.get("primary") or not provider_config.get("fallback"):
                            try:
                                temp_ocr = HandwritingOCR("dummy_key", provider=provider)
                                if not provider_config.get("primary"):
                                    provider_config["primary"] = temp_ocr.transcription_config["primary"].copy()
                                if not provider_config.get("fallback"):
                                    provider_config["fallback"] = temp_ocr.transcription_config["fallback"].copy()
                            except Exception:
                                # Use basic defaults if can't create temp OCR
                                if not provider_config.get("primary"):
                                    provider_config["primary"] = {"model": "", "prompt": ""}
                                if not provider_config.get("fallback"):
                                    provider_config["fallback"] = {"model": "", "prompt": ""}
        except Exception as e:
            print(f"Error loading settings: {e}")
            
    def save_settings(self):
        """Save settings to file."""
        try:
            settings = {
                "provider_configs": self.provider_configs,
                "selected_provider": self.selected_provider,
                "general_settings": self.general_settings,
            }
                
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
            
    def run(self):
        """Run the application."""
        self.root.mainloop()


def main():
    """Main function to run the GUI application."""
    # Set DPI awareness for Windows to handle high-DPI displays correctly
    if sys.platform == 'win32':
        try:
            from ctypes import windll
            # For Windows 10 v1607+, use Per-Monitor DPI-awareness v2 for best scaling results
            windll.shcore.SetProcessDpiAwareness(2)
        except (ImportError, AttributeError):
            # Fallback for older Windows versions
            try:
                from ctypes import windll
                windll.user32.SetProcessDPIAware()
            except (ImportError, AttributeError):
                pass

    try:
        app = OCRApp()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        messagebox.showerror("Startup Error", f"Failed to start application: {e}")


if __name__ == "__main__":
    main()
