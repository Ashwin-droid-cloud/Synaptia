#!/usr/bin/env python3
"""CLI interface for the AI Logic Puzzle system"""

import sys
import os
from dotenv import load_dotenv
from puzzle_generator import PuzzleGenerator
from hint_provider import HintProvider

load_dotenv()

class PuzzleCLI:
    """Command-line interface for puzzle generation and hint provision"""
    
    def __init__(self):
        """Initialize CLI"""
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            print("Error: OPENAI_API_KEY not found in environment variables")
            sys.exit(1)
        
        self.puzzle_gen = PuzzleGenerator(api_key)
        self.hint_provider = HintProvider(api_key)
        self.current_puzzle = None
        self.session_id = "cli_session"
    
    def run(self):
        """Run the CLI interface"""
        print("\n" + "="*60)
        print("  AI Logic Puzzle Generator & Hint Provider")
        print("="*60)
        self.show_menu()
        
        while True:
            try:
                choice = input("\n> Enter command (or 'help' for options): ").strip().lower()
                
                if choice == "quit" or choice == "exit":
                    print("\nThank you for playing! Goodbye!")
                    break
                elif choice == "help" or choice == "?":
                    self.show_menu()
                elif choice == "generate" or choice == "new":
                    self.generate_puzzle()
                elif choice == "hint":
                    self.show_hint()
                elif choice == "chat":
                    self.chat_with_bot()
                elif choice == "answer":
                    self.submit_answer()
                elif choice == "show":
                    self.show_current_puzzle()
                elif choice == "list":
                    self.list_puzzles()
                else:
                    print("Unknown command. Type 'help' for options.")
            
            except KeyboardInterrupt:
                print("\n\nInterrupted. Goodbye!")
                break
            except Exception as e:
                print(f"Error: {str(e)}")
    
    def show_menu(self):
        """Display help menu"""
        print("""
Commands:
  new/generate  - Generate a new puzzle
  show         - Show current puzzle
  hint         - Get a hint
  answer       - Submit your answer
  chat         - Chat with hint provider
  list         - List all puzzles
  help/?       - Show this menu
  quit/exit    - Exit the program
        """)
    
    def generate_puzzle(self):
        """Generate a new puzzle"""
        print("\nDifficulty levels: easy, medium, hard")
        difficulty = input("Choose difficulty (default: medium): ").strip().lower() or "medium"
        
        print("\nPuzzle types: riddle, math")
        puzzle_type = input("Choose type (default: riddle): ").strip().lower() or "riddle"
        
        print("\nGenerating puzzle...")
        puzzle = self.puzzle_gen.generate_puzzle(difficulty, puzzle_type)
        
        if "error" in puzzle:
            print(f"Error: {puzzle['error']}")
            return
        
        self.current_puzzle = puzzle
        self.hint_count = 0
        
        print(f"\n{'='*60}")
        print(f"Puzzle ID: {puzzle.get('id')}")
        print(f"Type: {puzzle.get('type', 'riddle').title()}")
        print(f"Difficulty: {puzzle.get('difficulty', 'medium').title()}")
        print(f"{'='*60}")
        print(f"\n{puzzle.get('question')}\n")
    
    def show_current_puzzle(self):
        """Display current puzzle"""
        if not self.current_puzzle:
            print("No puzzle loaded. Generate one first with 'new'.")
            return
        
        print(f"\n{'='*60}")
        print(f"Current Puzzle")
        print(f"{'='*60}")
        print(f"ID: {self.current_puzzle.get('id')}")
        print(f"Difficulty: {self.current_puzzle.get('difficulty', 'medium').title()}")
        print(f"Type: {self.current_puzzle.get('type', 'riddle').title()}")
        print(f"\n{self.current_puzzle.get('question')}\n")
    
    def show_hint(self):
        """Show a hint"""
        if not self.current_puzzle:
            print("No puzzle loaded. Generate one first with 'new'.")
            return
        
        hint = self.hint_provider.get_hint(self.current_puzzle, self.hint_count)
        print(f"\nHint {self.hint_count + 1}: {hint}\n")
        self.hint_count += 1
    
    def submit_answer(self):
        """Submit answer to puzzle"""
        if not self.current_puzzle:
            print("No puzzle loaded. Generate one first with 'new'.")
            return
        
        user_answer = input("\nYour answer: ").strip()
        result = self.puzzle_gen.check_answer(self.current_puzzle["id"], user_answer)
        
        if result.get("correct"):
            print("✓ Correct! Well done!")
        else:
            print(f"✗ That's not correct. Try again or get a hint.")
            if result.get("answer"):
                print(f"The answer was: {result['answer']}")
    
    def chat_with_bot(self):
        """Chat with the hint provider bot"""
        if not self.current_puzzle:
            print("No puzzle loaded. The bot will still chat with you!")
        
        print("\n[Chat mode - type 'exit' to return to main menu]")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() == "exit":
                    break
                
                if not user_input:
                    continue
                
                response = self.hint_provider.chat(
                    self.session_id,
                    user_input,
                    self.current_puzzle
                )
                
                print(f"Bot: {response}\n")
            
            except KeyboardInterrupt:
                print("\nExiting chat mode...")
                break
            except Exception as e:
                print(f"Error: {str(e)}")
    
    def list_puzzles(self):
        """List all generated puzzles"""
        puzzles = self.puzzle_gen.list_puzzles()
        
        if not puzzles:
            print("\nNo puzzles generated yet.")
            return
        
        print(f"\n{'='*60}")
        print("All Generated Puzzles")
        print(f"{'='*60}")
        
        for i, puzzle in enumerate(puzzles, 1):
            status = "✓ Solved" if puzzle.get("solved") else "⏳ Unsolved"
            print(f"\n{i}. {puzzle.get('type', 'riddle').title()} - {puzzle.get('difficulty', 'medium').title()}")
            print(f"   ID: {puzzle.get('id')}")
            print(f"   Status: {status}")
            print(f"   Created: {puzzle.get('created_at', 'N/A')[:10]}")

def main():
    """Main entry point"""
    cli = PuzzleCLI()
    cli.run()

if __name__ == "__main__":
    main()
