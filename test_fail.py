import os
from puzzle_generator import PuzzleGenerator

generator = PuzzleGenerator(os.getenv("GEMINI_API_KEY"))
res = generator.generate_puzzle()
print("RESULT:", res)
