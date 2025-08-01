# kernel_manager.py
# © 2025 Colt McVey
# Manages Jupyter kernels for code execution in notebooks.

import sys
from jupyter_client.manager import KernelManager
from queue import Empty
import uuid

class NotebookKernel:
    """
    A wrapper around a Jupyter kernel for a single notebook instance.
    This class handles starting, stopping, and executing code in a kernel.
    """
    def __init__(self):
        self.km = KernelManager()
        self.km.start_kernel()
        print(f"Kernel started: {self.km.kernel_id}")
        self.kc = self.km.client()
        self.kc.start_channels()
        
        # Ensure the kernel is fully ready
        try:
            self.kc.wait_for_ready(timeout=60)
            print("Kernel client is ready.")
        except RuntimeError:
            print("Timeout waiting for kernel to be ready.")
            self.shutdown()

    def execute(self, code: str) -> dict:
        """
        Executes a block of code in the kernel and returns the result.
        
        Args:
            code: The string of code to execute.
            
        Returns:
            A dictionary containing the output, errors, and any rich data.
        """
        if not self.kc.is_alive():
            print("Cannot execute code, kernel is not alive.")
            return {"status": "error", "output": "Kernel is not running."}

        msg_id = self.kc.execute(code)
        
        outputs = []
        
        while True:
            try:
                # The iopub channel broadcasts results, errors, etc.
                msg = self.kc.get_iopub_msg(timeout=5)
                
                # Check if the message is for our execution request
                if msg['parent_header'].get('msg_id') != msg_id:
                    continue

                msg_type = msg['header']['msg_type']
                content = msg['content']

                if msg_type == 'status':
                    if content['execution_state'] == 'idle':
                        # Execution is complete
                        break
                elif msg_type == 'stream':
                    outputs.append({'type': 'stdout', 'text': content['text']})
                elif msg_type == 'display_data':
                    # For rich outputs like images, plots
                    data = content['data']
                    if 'text/plain' in data:
                        outputs.append({'type': 'display', 'text': data['text/plain']})
                elif msg_type == 'execute_result':
                    # The final result of the code
                     outputs.append({'type': 'result', 'text': content['data'].get('text/plain', '')})
                elif msg_type == 'error':
                    error_text = '\n'.join(content['traceback'])
                    outputs.append({'type': 'error', 'text': error_text})

            except Empty:
                print("Timeout waiting for kernel message.")
                break
        
        return {"status": "ok", "outputs": outputs}

    def shutdown(self):
        """Shuts down the kernel and cleans up resources."""
        print(f"Shutting down kernel: {self.km.kernel_id}")
        if self.kc and self.kc.is_alive():
            self.kc.stop_channels()
        if self.km and self.km.is_alive():
            self.km.shutdown_kernel()


class KernelManagerService:
    """
    A global service to manage kernels for all open notebooks.
    """
    def __init__(self):
        self.kernels: dict[str, NotebookKernel] = {}

    def start_kernel_for_notebook(self, notebook_id: str) -> NotebookKernel:
        """Starts a new kernel for a given notebook ID."""
        if notebook_id in self.kernels:
            return self.kernels[notebook_id]
        
        print(f"Starting new kernel for notebook {notebook_id}")
        kernel = NotebookKernel()
        self.kernels[notebook_id] = kernel
        return kernel

    def get_kernel(self, notebook_id: str) -> NotebookKernel | None:
        """Gets the kernel for a given notebook ID."""
        return self.kernels.get(notebook_id)

    def shutdown_kernel(self, notebook_id: str):
        """Shuts down the kernel for a specific notebook."""
        if notebook_id in self.kernels:
            self.kernels[notebook_id].shutdown()
            del self.kernels[notebook_id]

    def shutdown_all(self):
        """Shuts down all managed kernels."""
        print("Shutting down all kernels...")
        for notebook_id in list(self.kernels.keys()):
            self.shutdown_kernel(notebook_id)

# --- Global Instance ---
# A single instance of the service to be used by the application
kernel_manager_service = KernelManagerService()