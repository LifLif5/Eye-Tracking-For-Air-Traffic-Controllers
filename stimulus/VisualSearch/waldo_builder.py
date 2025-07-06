import pygame, json, os, glob
import ctypes
ctypes.windll.user32.SetProcessDPIAware()  # Ensure high DPI awareness for Windows
# Setup
IMG_FOLDER = "stimulus/VisualSearch/waldo_images"
SAVE_PATH  = os.path.join(IMG_FOLDER, "waldo_boxes.json")

# Load image list
images = sorted(glob.glob(f"{IMG_FOLDER}/*.jpg"))
boxes = {}
idx = 0

pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 40)

drawing = False
start_pos = None
current_box = None

def draw_image_with_box(img_path, box=None):
    screen.fill((255, 255, 255))
    img = pygame.image.load(img_path)
    img = pygame.transform.scale(img, screen.get_size())
    screen.blit(img, (0, 0))
    if box:
        pygame.draw.rect(screen, (255, 0, 0), box, 3)
    text = font.render(f"{os.path.basename(img_path)}", True, (0, 0, 0))
    screen.blit(text, (50, 50))
    pygame.display.flip()

while idx < len(images):
    img_path = images[idx]
    draw_image_with_box(img_path)

    running = True
    while running:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                idx = len(images)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); exit()
                elif event.key == pygame.K_s and current_box:
                    # Save box
                    boxes[os.path.basename(img_path)] = list(current_box)
                    print("Saved:", current_box)
                    current_box = None
                    idx += 1
                    running = False
                elif event.key == pygame.K_RIGHT:
                    idx += 1
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                start_pos = event.pos
                drawing = True
            elif event.type == pygame.MOUSEBUTTONUP and drawing:
                end_pos = event.pos
                x = min(start_pos[0], end_pos[0])
                y = min(start_pos[1], end_pos[1])
                w = abs(end_pos[0] - start_pos[0])
                h = abs(end_pos[1] - start_pos[1])
                current_box = pygame.Rect(x, y, w, h)
                draw_image_with_box(img_path, current_box)
                drawing = False

# Save all boxes
with open(SAVE_PATH, "w") as f:
    json.dump({k: [int(x) for x in v] for k, v in boxes.items()}, f, indent=2)
print(f"Saved {len(boxes)} boxes to {SAVE_PATH}")
pygame.quit()
