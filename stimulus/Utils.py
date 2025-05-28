
import math
import random
import tkinter as tk

# Initialize tkinter to get screen dimensions
root = tk.Tk()
root.withdraw()
WIDTH = root.winfo_screenwidth()
HEIGHT = root.winfo_screenheight()



# Colors
WHITE, RED, GREEN, BLACK = (255,255,255), (255,0,0), (0,255,0), (0,0,0)
BLUE = (0, 0, 255)

def generate_grid_positions(n_items, jitter=True):
    aspect_ratio = WIDTH / HEIGHT
    cols = math.ceil(math.sqrt(n_items * aspect_ratio))
    rows = math.ceil(n_items / cols)

    cell_w = WIDTH / cols
    cell_h = HEIGHT / rows

    grid_positions = []
    for r in range(rows):
        for c in range(cols):
            if len(grid_positions) >= n_items:
                break
            x = c * cell_w + cell_w / 2
            y = r * cell_h + cell_h / 2
            if jitter:
                x += random.uniform(-cell_w * 0.25, cell_w * 0.25)
                y += random.uniform(-cell_h * 0.25, cell_h * 0.25)
            grid_positions.append((int(x), int(y)))
    random.shuffle(grid_positions)
    return grid_positions