import threading
import webview
import back_end


def run_backend():
    back_end.start_assistant()
    



if __name__ == "__main__":
    # Start assistant in background thread
    backend_thread = threading.Thread(target=run_backend)
    backend_thread.daemon = True
    backend_thread.start()

    # Launch UI window
    webview.create_window(
        "REN AI",
        "ui.html",
        fullscreen=True
    )

    webview.start()
