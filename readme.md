## Note:
- sas.py works mostly fine.
- sas1.py contains an additional _display_response() function, and a modified interactive_loop() function to handle the cases when the openai API doesn't generate a valid code.
- sas2.py is similar to sas1.py except:
    1. Removed Redundant Retry Logic
        > The original code had a retry mechanism (while retries < MAX_RETRIES), but in practice, the feedback improvement process should be a single step unless explicitly designed for iterative refinement.
        > If the response requires further clarification, the user should provide additional input naturally, rather than looping within the same function.

    2. Streamlined Code Flow
        > The original implementation separated cases for improved solutions, clarifications, and invalid responses within a loop.
        > The new version assumes that the model’s response will be directly useful, and if further clarification is needed, it can be handled naturally by re-submitting feedback.

    3. Ensured Feedback is Stored Consistently
        > The conversation_history.append((query, response, feedback)) is called immediately after receiving feedback, ensuring that all interactions are logged properly.

    4. Directly Processes the Feedback
        > Instead of checking conditions and looping, the function now directly improves the response and displays it, making the interaction smoother.
- sas2.py has not been tested by me (for that reson I would rely more on sas1.py), but this script should work fine mostly.
