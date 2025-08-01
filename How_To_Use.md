How to Use 💩 CRAP 3.0
Welcome to Colt's Ridiculously Arrogant Programmer! This guide will walk you through the main features of the application, showing you how to leverage its powerful AI capabilities to create a fast, fluid, and intelligent "vibe coding" experience.

1. The Reactive Notebook: Your Live Coding Environment
The notebook is your primary workspace. Unlike traditional notebooks, CRAP 3.0's notebook is reactive: when you change a cell, any other cell that depends on its output will re-run automatically.

Example: Reactive Execution
Create a cell with a = 10. Run it.

Create a second cell with b = 5. Run it.

Create a third cell with c = a + b; print(f"The sum is {c}"). Run it. The output will be The sum is 15.

Now, go back to the first cell and change it to a = 100. As soon as you finish editing, the third cell will automatically re-run, and its output will instantly update to The sum is 105.

Running Code Manually
Run a single cell and its dependents: Click the Play (▶) icon on the left side of any code cell.

Run all cells: Click the Fast-Forward (») icon in the main notebook toolbar to run all code cells in the correct order.

Writing and Running Tests
Write your code in a normal cell.

In a new cell, check the "Mark as Test" box in the top-right corner. The cell will turn green.

Write your test code using standard Python assertions.

Click the Checkmark (✓) icon in the main notebook toolbar to run only the test cells.

2. The AI Chat & Context System
The AI Chat is your primary partner. Its power comes from its deep understanding of your project's context.

Providing Context
There are three ways to give the AI context:

File Browser (Left Panel): Click "Upload Files" to add one or more files to the AI's long-term memory for this session. This is perfect for providing library code, data files, or documentation. The AI will use its RAG engine to find the most relevant parts of these files for your questions.

Scratchpad (Left Panel): Use the scratchpad as your personal canvas. You can collect code snippets from the AI, edit them, and organize your thoughts. The contents of the scratchpad are not automatically sent to the AI.

Editor Context: Simply select code in your active notebook cell. The AI will always see your current selection.

Asking Follow-up Questions
The AI Chat now has a memory of your current conversation. You can ask follow-up questions like:

"That's a good start, but can you refactor that last function to be more efficient?"

Click the "New Chat" button to clear the history and start a fresh conversation.

3. The "Vibe Check": Your AI Code Reviewer
The "Vibe Check" is the heart of the "arrogant programmer" concept. It's your personal AI code reviewer that you can invoke at any time to analyze and improve your code.

How to Use AI-Powered Refactoring
The refactoring tool is accessed via a right-click context menu within any code cell. This is a powerful feature for when you have code that works, but you feel it could be cleaner, more efficient, or more idiomatic.

Write Your Code: Write a function, class, or any block of code in a code cell.

Right-Click: Move your mouse over the code you want to improve and right-click to open the context menu.

Select "Vibe Check: Refactor Code":

You will see an option in the menu labeled Vibe Check: Refactor Code. Click it.

Review the Changes: The AI will analyze your code and replace it in-place with an improved, more professional version. The AI's goal is to improve readability and performance while preserving the original functionality.

Tip: This works best on self-contained blocks of logic, like a single function or class. The AI will add comments to explain complex changes it makes.

Generating Tests and Docstrings
Write a function or class.

Right-click on the cell.

Select "Generate Tests". A new, green test cell will be created below with a complete unittest suite for your code.

Right-click again and select "Generate Docstring". The AI will write a professional, Google-style docstring and insert it directly into your code.

4. The App Factory: From Idea to Application
The App Factory can generate an entire, runnable project from a single prompt.

Go to the "App Factory" tab.

In the "Describe Your Application" box, write a detailed description.

Example: "Create a Python Flask web server with a single API endpoint /api/data that returns a simple JSON object. Include a templates folder with a basic index.html file and a .github/workflows directory with a CI pipeline that runs tests."

Choose a project name and directory.

Click "Generate Application".

After generation, open any of the generated files in a notebook. The AI Chat will now be project-aware. It automatically knows the original prompt and the complete architectural plan, allowing you to have intelligent follow-up conversations like:

"You forgot to add the database connection file. Please generate the code for server/db.js."