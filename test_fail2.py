import os
from dotenv import load_dotenv
from puzzle_generator import PuzzleGenerator

load_dotenv()
generator = PuzzleGenerator(os.getenv("GEMINI_API_KEY"))
res = generator.generate_puzzle()
print("RESULT:", res)
