import os
import sys
import threading
import webview
import json
from back_end import start_assistant
from system_monitor import system_status

class Api:
    def __init__(self):
        self.stop_event = threading.Event()
        self.assistant_thread = None
        self._window = None
        self._ui_callback = None


    def start_assistant(self):
        if self.assistant_thread and self.assistant_thread.is_alive():
            return "Assistant is already running."
        
        self.stop_event.clear()
        
        # Build UI callback bridge
        def ui_callback(event_type, data):
            if not self._window:
                return
            try:
                if event_type == 'status':
                    self._window.evaluate_js(f"window.updateStatus({json.dumps(data)});")
                elif event_type == 'user_speech':
                    self._window.evaluate_js(f"window.updateUserSpeech({json.dumps(data)});")
                elif event_type == 'assistant_speech':
                    self._window.evaluate_js(f"window.updateAssistantSpeech({json.dumps(data)});")
                elif event_type == 'module_status':
                    module_name, status_text, is_active = data
                    self._window.evaluate_js(f"window.updateModuleStatus({json.dumps(module_name)}, {json.dumps(status_text)}, {json.dumps(is_active)});")
                elif event_type == 'show_popup':
                    self._window.evaluate_js(f"window.showPopup({json.dumps(data)});")
                elif event_type == 'skills_list':
                    self._window.evaluate_js(f"window.updateSkillsList({json.dumps(data)});")
                elif event_type == 'reflect_mode':
                    self._window.evaluate_js(f"window.setReflectMode({json.dumps(data['active'])}, {json.dumps(data['logs'])});")
                elif event_type == 'agent_stage':
                    self._window.evaluate_js(f"window.updatePipelineStage({json.dumps(data)});")
            except Exception as e:
                print(f"Error in UI callback: {e}", file=sys.stderr)

        self._ui_callback = ui_callback
        self.assistant_thread = threading.Thread(
            target=start_assistant, 
            args=(ui_callback, self.stop_event),
            daemon=True
        )
        self.assistant_thread.start()
        return "Cognitive assistant background thread spawned successfully."

    def get_system_status(self):
        try:
            return system_status()
        except Exception as e:
            print(f"System status error: {e}", file=sys.stderr)
            return None

    def submit_prompt(self, prompt):
        from back_end import submit_typed_prompt
        submit_typed_prompt(prompt)
        return "Prompt received by REN-AI Core."

    def refresh_skills(self):
        from back_end import refresh_skills_ui
        refresh_skills_ui()
        return "Skills list refreshed."

    def enter_reflect_mode(self):
        import back_end
        if back_end.is_processing:
            return "Cognitive focus active. Postponing reflection sequence."
        
        back_end.awake = False
        logs = back_end.get_dream_logs()
        self._window.evaluate_js(f"window.setReflectMode(true, {json.dumps(logs)})")
        back_end.start_dream_daemon(self._ui_callback)
        return "Cognitive reflection cycle initialized."

    def exit_reflect_mode(self):
        import back_end
        back_end.awake = True
        self._window.evaluate_js("window.setReflectMode(false)")
        return "Cognitive core waking up."

    def stop_operations(self):
        import back_end
        result = back_end.stop_operations()
        self._window.evaluate_js("window.updatePipelineStage('idle');")
        return result

def main():
    api = Api()
    
    # Get absolute path to index.html
    gui_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'gui'))
    html_path = os.path.join(gui_dir, 'index.html')
    
    if not os.path.exists(html_path):
        print(f"Error: GUI files not found at {html_path}", file=sys.stderr)
        sys.exit(1)
        
    # Configure and create pywebview window
    window = webview.create_window(
        title='REN AI', 
        url=html_path, 
        js_api=api,
        width=1024,
        height=720,
        min_size=(800, 600),
        resizable=True,
        background_color='#020617' # Deep dark slate color matching CSS to avoid flashes
    )
    api._window = window
    
    print("Launching pywebview window...")
    webview.start(gui='edgechromium', debug=True)

if __name__ == '__main__':
    main()
