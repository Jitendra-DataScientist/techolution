"""
    a) This script contains code for one of Techolution's assignments.
    b) This script is tested, and in that could be said to be better than sas2.py.
"""
import openai
import re
import subprocess
import tempfile
import os
import ast
import logging
from dotenv import load_dotenv

# Determine the directory for logs
log_directory = os.path.join(os.getcwd(), 'logs')

# Create the logs directory if it doesn't exist
if not os.path.exists(log_directory):
    os.mkdir(log_directory)


# Create a logger instance
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a file handler for this script's log file
file_handler = logging.FileHandler(os.path.join(log_directory, "dashboard.log"))
file_handler.setLevel(logging.DEBUG)  # Set the logging level for this handler

# Create a formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)

# Load environment variables from a .env file
load_dotenv()


class IntelligentCodingAgent:
    def __init__(self, api_key):
        """
        Initializes the Intelligent Coding Agent.
        
        Parameters:
        api_key (str): OpenAI API key for generating code responses.
        """
        openai.api_key = api_key
        self.conversation_history = []  # Stores past interactions for context
        self.safety_checks = {
            "banned_imports": {"os", "sys", "subprocess"},  # Restricted imports for security
            "allowed_functions": set(),  # Allowed functions (can be expanded as needed)
            "time_limit": 5  # Execution timeout in seconds
        }


    def _generate_response(self, prompt, max_tokens=1500):
        """
        Generates a response using OpenAI's GPT-4 model.
        
        Parameters:
        prompt (str): User query for generating code.
        max_tokens (int): Token limit for the response.
        
        Returns:
        str: Generated response from the model.
        """
        messages = [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": prompt}
        ]
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.3  # Lower temperature for more deterministic responses
        )
        return response.choices[0].message.content


    def _system_prompt(self):
        """
        Defines the system prompt for guiding the AI assistant.
        
        Returns:
        str: System instruction string.
        """
        return """You are an expert Python developer. Follow these rules:
                    1. If request is unclear, ask ONE clarifying question
                    2. Generate production-quality code with:
                    - Error handling
                    - Type hints
                    - Docstrings
                    - Modular structure
                    3. Explain the code with:
                    - Functionality overview
                    - Performance analysis
                    - Assumptions
                    - Complexity analysis
                    4. Use secure coding practices
                    5. Format response as:
                    [CLARIFICATION] <question> or
                    [CODE]
                    ```python
                    <code>
                    [EXPLANATION]
                    <detailed explanation>
            """


    def _validate_code_safety(self, code):
        """
        Validates whether the generated code is safe to execute by checking for restricted imports.
        
        Parameters:
        code (str): Python code to validate.
        
        Returns:
        bool: True if the code is safe, False otherwise.
        """
        try:
            tree = ast.parse(code)  # Parse the code into an AST (Abstract Syntax Tree)
            for node in ast.walk(tree):  # Traverse the AST to inspect imports
                if isinstance(node, ast.Import):
                    for name in node.names:
                        if name.name.split('.')[0] in self.safety_checks["banned_imports"]:
                            return False
                elif isinstance(node, ast.ImportFrom):
                    if node.module.split('.')[0] in self.safety_checks["banned_imports"]:
                        return False
            return True  # Code passes validation
        except:
            return False  # If parsing fails, assume the code is unsafe


    def _execute_safely(self, code):
        """
        Executes the given code in a controlled environment.
        
        Parameters:
        code (str): Python code to execute.
        
        Returns:
        str: Execution output or error message.
        """
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode='w') as f:
            f.write(code)
            filename = f.name  # Store the filename for execution
        
        try:
            result = subprocess.run(
                ["python", filename],
                capture_output=True,
                text=True,
                timeout=self.safety_checks["time_limit"],
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Error: {e.stderr}"
        except subprocess.TimeoutExpired:
            return "Execution timed out"
        finally:
            os.remove(filename)  # Ensure cleanup after execution


    def process_query(self, query):
        """
        Processes a user query to generate and execute Python code.
        
        Parameters:
        query (str): User input describing the coding task.
        
        Returns:
        dict: Contains generated code, explanation, and execution result.
        """
        response = self._generate_response(query)
        
        if "[CLARIFICATION]" in response:
            return {"type": "clarification", "content": response.split("]")[1].strip()}
        
        code_match = re.search(r'\[CODE\](.*?)\[EXPLANATION\]', response, re.DOTALL)
        explanation = response.split("[EXPLANATION]")[-1].strip()
        
        if code_match:
            code = re.search(r'```python(.*?)```', code_match.group(1), re.DOTALL)
            if code:
                code = code.group(1).strip()
                if self._validate_code_safety(code):
                    execution_result = self._execute_safely(code)
                else:
                    execution_result = "Code blocked due to security restrictions"
            else:
                code = "Invalid code format"
                execution_result = ""
        else:
            code = "No code generated"
            execution_result = ""

        return {
            "type": "solution",
            "code": code,
            "explanation": explanation,
            "execution_result": execution_result
        }


    def interactive_loop(self):
        """
        Interactive loop for user input and code generation.
        """
        MAX_RETRIES = 3  # Maximum attempts to get valid code
        
        while True:
            query = input("\nEnter your coding task (or 'quit' to exit): ")
            if query.lower() == 'quit':
                break
            
            response = self.process_query(query)
            
            # Handle initial clarification
            if response["type"] == "clarification":
                print(f"\nClarification needed: {response['content']}")
                clarification = input("Your clarification: ")
                query += f"\nUser clarification: {clarification}"
                response = self.process_query(query)
            
            # Process initial solution
            if response["type"] == "solution":
                self._display_response(response)
                feedback = input("\nProvide feedback (or press enter to continue): ")
                
                if feedback:
                    retries = 0
                    while retries < MAX_RETRIES:
                        self.conversation_history.append((query, response, feedback))
                        print("Feedback received. Improving solution...")
                        improved_response = self.process_query(f"{query}\nUser feedback: {feedback}")
                        
                        # Handle improved solution
                        if improved_response["type"] == "solution":
                            self._display_response(improved_response, prefix="IMPROVED")
                            break
                        
                        # Handle follow-up clarification
                        elif improved_response["type"] == "clarification":
                            print(f"\nClarification needed: {improved_response['content']}")
                            clarification = input("Your clarification: ")
                            feedback += f"\nUser clarification: {clarification}"
                            retries += 1
                        
                        # Handle invalid response format
                        else:
                            print("Unexpected response format. Please try again.")
                            retries += 1
                    
                    if retries >= MAX_RETRIES:
                        print("Maximum retry attempts reached. Please refine your query.")


    def _display_response(self, response, prefix="GENERATED"):
        """
        Displays the generated code, explanation, and execution result.
        """
        print(f"\n=== {prefix} CODE ===")
        print(response.get("code", "No code generated"))
        print(f"\n=== {prefix} EXPLANATION ===")
        print(response.get("explanation", "No explanation available"))
        print("\n=== EXECUTION RESULT ===")
        print(response.get("execution_result", "No execution result available"))


if __name__ == "__main__":
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")
    agent = IntelligentCodingAgent(api_key)
    agent.interactive_loop()
