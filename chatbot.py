"""
Interactive chatbot using GPT-4o-mini for headache tracking assistance.

This chatbot can:
- Answer questions about headache tracking
- Analyze headache data from Google Sheets
- Provide insights and recommendations
- Help with general health questions
"""

import os
import sys
import time
from typing import List, Dict, Optional

from dotenv import load_dotenv
from openai import OpenAI

# Import headache data fetcher
from fetch_headache_data import HeadacheDataFetcher

# Load environment variables
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4o-mini"

# ANSI color codes for terminal output
class Colors:
    """Terminal color codes."""
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


class HeadacheChatbot:
    """Interactive chatbot for headache tracking assistance."""

    def __init__(self, api_key: str, model: str = MODEL):
        """
        Initialize the chatbot.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o-mini)
        """
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.conversation_history: List[Dict[str, str]] = []
        self.headache_fetcher = None
        self.headache_data = None  # Store fetched data in memory
        self.data_loaded = False  # Track if data has been loaded

        # System message to set context
        self.system_message = """You are a helpful, empathetic assistant for tracking and analyzing headaches. 
You specialize in helping users:
- Understand their headache patterns and trends
- Analyze headache data from their tracking records
- Identify potential triggers, medication effectiveness, and pain level patterns
- Answer questions about headache management and prevention
- Provide personalized recommendations based on their data

Guidelines:
- Be friendly, empathetic, and supportive
- Use data-driven insights when available
- Look for patterns, trends, and correlations in the data
- Provide actionable recommendations
- Format your responses clearly with bullet points or numbered lists when helpful
- Be concise but thorough"""

        # Initialize conversation with system message
        self.conversation_history.append(
            {"role": "system", "content": self.system_message}
        )

    def initialize_headache_fetcher(self):
        """Initialize the headache data fetcher if not already done."""
        if self.headache_fetcher is None:
            try:
                service_account_path = os.getenv("SERVICE_ACCOUNT_PATH")
                drive_folder_id = os.getenv("DRIVE_FOLDER_ID")
                self.headache_fetcher = HeadacheDataFetcher(
                    service_account_path=service_account_path,
                    drive_folder_id=drive_folder_id,
                )
                # Suppress print statements from fetcher during initialization
                return True
            except Exception as e:
                return False

    def load_headache_data(self, silent: bool = False, force_reload: bool = False) -> Optional[List[Dict]]:
        """
        Load headache data from Google Sheets into memory.

        Args:
            silent: If True, suppress print statements
            force_reload: If True, reload data even if already loaded

        Returns:
            List of headache records or None if error
        """
        # Return cached data if already loaded and not forcing reload
        if self.data_loaded and not force_reload:
            return self.headache_data

        if self.headache_fetcher is None:
            if not self.initialize_headache_fetcher():
                if not silent:
                    print(f"{Colors.RED}❌ Could not initialize headache data fetcher{Colors.END}")
                return None

        if self.headache_fetcher is None:
            return None

        try:
            # Temporarily redirect stdout if silent mode
            if silent:
                import io
                from contextlib import redirect_stdout
                f = io.StringIO()
                with redirect_stdout(f):
                    data = self.headache_fetcher.get_headache_data()
            else:
                data = self.headache_fetcher.get_headache_data()
            
            # Store in memory
            self.headache_data = data
            self.data_loaded = True
            
            # Add data context to conversation history (once)
            if data and not force_reload:
                data_summary = self._format_headache_data(data)
                self.conversation_history.append(
                    {
                        "role": "system",
                        "content": f"User's headache tracking data (loaded at start of conversation):\n\n{data_summary}\n\nThis data is available for analysis throughout the conversation.",
                    }
                )
            
            return data
        except Exception as e:
            if not silent:
                print(f"{Colors.RED}❌ Error fetching headache data: {e}{Colors.END}")
            return None

    def chat(self, user_message: str, show_typing: bool = True) -> str:
        """
        Send a message to the chatbot and get a response.

        Args:
            user_message: The user's message
            show_typing: Show typing indicator

        Returns:
            The chatbot's response
        """
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_message})

        try:
            if show_typing:
                print(f"{Colors.CYAN}💭 Thinking...{Colors.END}", end="", flush=True)
            
            # Get response from OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                temperature=0.7,
                max_tokens=1500,
            )

            assistant_message = response.choices[0].message.content

            # Add assistant response to history
            self.conversation_history.append(
                {"role": "assistant", "content": assistant_message}
            )

            if show_typing:
                print(f"\r{Colors.GREEN}✓{Colors.END} ", end="", flush=True)
                time.sleep(0.2)

            return assistant_message

        except Exception as e:
            if show_typing:
                print(f"\r{Colors.RED}✗{Colors.END} ", end="", flush=True)
            error_msg = f"{Colors.RED}❌ Error: {str(e)}{Colors.END}"
            return error_msg

    def _format_headache_data(self, data: List[Dict]) -> str:
        """
        Format headache data for the chatbot context.

        Args:
            data: List of headache records

        Returns:
            Formatted string representation of the data
        """
        if not data:
            return "No headache data found."

        formatted = f"Total records: {len(data)}\n\n"
        for i, record in enumerate(data, 1):
            formatted += f"--- Record {i} ---\n"
            for key, value in record.items():
                if not key.startswith("_"):
                    # Clean up key names (remove extra spaces, colons)
                    clean_key = key.strip().rstrip(":")
                    formatted += f"{clean_key}: {value}\n"
            formatted += "\n"

        return formatted

    def reset_conversation(self, keep_data: bool = True):
        """
        Reset the conversation history.
        
        Args:
            keep_data: If True, keep the loaded headache data in context
        """
        self.conversation_history = [{"role": "system", "content": self.system_message}]
        
        # Re-add data context if it was loaded and we want to keep it
        if keep_data and self.data_loaded and self.headache_data:
            data_summary = self._format_headache_data(self.headache_data)
            self.conversation_history.append(
                {
                    "role": "system",
                    "content": f"User's headache tracking data:\n\n{data_summary}\n\nThis data is available for analysis throughout the conversation.",
                }
            )
        
        print(f"{Colors.YELLOW}🔄 Conversation reset{Colors.END}")


def print_header():
    """Print the chatbot header."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}🤖  Headache Tracking Assistant{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}Powered by GPT-4o-mini{Colors.END}\n")


def print_help():
    """Print help information."""
    print(f"\n{Colors.BOLD}Commands:{Colors.END}")
    print(f"  {Colors.GREEN}help{Colors.END}     - Show this help message")
    print(f"  {Colors.GREEN}reload{Colors.END}   - Reload headache data from Google Sheets")
    print(f"  {Colors.GREEN}reset{Colors.END}    - Reset conversation history (keeps data in memory)")
    print(f"  {Colors.GREEN}quit/exit{Colors.END} - Exit the chatbot")
    print(f"\n{Colors.BOLD}Tips:{Colors.END}")
    print(f"  • Your headache data is loaded once at startup for efficiency")
    print(f"  • Ask about patterns, triggers, medications, or request analysis")
    print(f"  • The chatbot remembers your conversation context")
    print(f"{Colors.DIM}{'─'*60}{Colors.END}\n")


def main():
    """Main function to run the interactive chatbot."""
    print_header()

    # Check for API key
    if not OPENAI_API_KEY:
        print(f"{Colors.RED}❌ ERROR: OPENAI_API_KEY not found in .env file!{Colors.END}")
        print(f"{Colors.YELLOW}Please add your OpenAI API key to the .env file:{Colors.END}")
        print(f"{Colors.DIM}OPENAI_API_KEY=your_api_key_here{Colors.END}")
        return

    # Initialize chatbot
    try:
        print(f"{Colors.CYAN}Initializing chatbot...{Colors.END}", end="", flush=True)
        chatbot = HeadacheChatbot(api_key=OPENAI_API_KEY)
        print(f" {Colors.GREEN}✓{Colors.END}\n")
    except Exception as e:
        print(f" {Colors.RED}✗{Colors.END}")
        print(f"{Colors.RED}❌ Error initializing chatbot: {e}{Colors.END}")
        return

    # Load headache data at startup
    print(f"{Colors.CYAN}Loading headache data...{Colors.END}", end="", flush=True)
    data = chatbot.load_headache_data(silent=True)
    if data:
        print(f" {Colors.GREEN}✓{Colors.END}")
        print(f"{Colors.GREEN}✅ Loaded {len(data)} headache record(s) into memory{Colors.END}\n")
    else:
        print(f" {Colors.YELLOW}⚠{Colors.END}")
        print(f"{Colors.YELLOW}⚠️  Could not load headache data (you can still use the chatbot){Colors.END}\n")

    print_help()

    # Interactive loop
    while True:
        try:
            # Get user input with colored prompt
            user_input = input(f"{Colors.BOLD}{Colors.BLUE}You:{Colors.END} ").strip()

            # Check for exit commands
            if user_input.lower() in ["quit", "exit", "bye", "q"]:
                print(f"\n{Colors.GREEN}👋 Goodbye! Take care of your health!{Colors.END}\n")
                break

            # Check for help command
            if user_input.lower() in ["help", "h", "?"]:
                print_help()
                continue

            # Check for reset command
            if user_input.lower() == "reset":
                chatbot.reset_conversation(keep_data=True)
                print()
                continue

            # Check for reload command
            if user_input.lower() == "reload":
                print(f"\n{Colors.CYAN}🔄 Reloading headache data...{Colors.END}", end="", flush=True)
                data = chatbot.load_headache_data(silent=True, force_reload=True)
                if data:
                    print(f" {Colors.GREEN}✓{Colors.END}")
                    print(f"{Colors.GREEN}✅ Reloaded {len(data)} record(s){Colors.END}\n")
                else:
                    print(f" {Colors.RED}✗{Colors.END}")
                    print(f"{Colors.RED}❌ Could not reload headache data{Colors.END}\n")
                continue

            # Skip empty input
            if not user_input:
                continue

            # Get response from chatbot
            print(f"\n{Colors.BOLD}{Colors.CYAN}Assistant:{Colors.END} ", end="", flush=True)
            response = chatbot.chat(user_input)
            # Print response with proper formatting
            print(response)
            print()

        except KeyboardInterrupt:
            print(f"\n\n{Colors.GREEN}👋 Goodbye! Take care of your health!{Colors.END}\n")
            break
        except Exception as e:
            print(f"\n{Colors.RED}❌ Error: {e}{Colors.END}\n")


if __name__ == "__main__":
    main()
