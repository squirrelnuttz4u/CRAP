# debugger_logic.py
# © 2025 Colt McVey
# The backend logic for the integrated debugger.

import logging
from PySide6.QtCore import QObject, Signal
from kernel_manager import NotebookKernel

class DebuggerLogic(QObject):
    """
    Manages the debugging session for a single kernel, communicating
    with the Jupyter debugging protocol.
    """
    stopped = Signal(list, list) # stack, variables
    continued = Signal()
    finished = Signal()

    def __init__(self, kernel: NotebookKernel):
        super().__init__()
        self.kernel = kernel
        self.kc = kernel.kc
        # In a real app, you would start a dedicated thread to listen for debug events.
        # For simplicity here, we will poll, but this is not ideal.

    def start_debugging(self, code: str, breakpoints: list):
        """Starts a debugging session by executing code with debugging info."""
        # This is a simplified representation. The real DAP protocol is more complex.
        logging.info(f"Starting debug session for code with breakpoints: {breakpoints}")
        # In a real implementation, you would send a `debugRequest` to the kernel.
        # For now, we simulate a stop event after a simple execution.
        result = self.kernel.execute(code)
        
        # Simulate stopping at a breakpoint
        simulated_stack = [
            {'name': 'my_function', 'file': 'cell_1', 'line': 2},
            {'name': '<module>', 'file': 'cell_1', 'line': 5}
        ]
        simulated_vars = [
            {'name': 'a', 'type': 'int', 'value': '10'},
            {'name': 'b', 'type': 'int', 'value': '5'}
        ]
        self.stopped.emit(simulated_stack, simulated_vars)

    def continue_execution(self):
        logging.info("Debugger: Continue")
        # In a real implementation, send a 'continue' debug request.
        self.continued.emit()
        self.finished.emit() # Simulate finishing

    def step_over(self):
        logging.info("Debugger: Step Over")
        # In a real implementation, send a 'next' debug request.
        
    def step_in(self):
        logging.info("Debugger: Step In")
        # In a real implementation, send a 'stepIn' debug request.

    def step_out(self):
        logging.info("Debugger: Step Out")
        # In a real implementation, send a 'stepOut' debug request.
