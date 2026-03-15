from PIL import Image, ImageDraw, ImageFont
import os

# Brand Colors
OBSIDIAN = (5, 5, 5)
NEURAL_BLUE = (0, 122, 255)
WHITE = (255, 255, 255)

def generate_pfp():
    # 800x800 PFP - Higher resolution for validation
    img = Image.new('RGB', (800, 800), color=OBSIDIAN)
    draw = ImageDraw.Draw(img)
    
    # Radial Gradient Simulation
    for r in range(400, 0, -1):
        color = (
            int(OBSIDIAN[0] + (NEURAL_BLUE[0] - OBSIDIAN[0]) * (1 - r/400) * 0.2),
            int(OBSIDIAN[1] + (NEURAL_BLUE[1] - OBSIDIAN[1]) * (1 - r/400) * 0.2),
            int(OBSIDIAN[2] + (NEURAL_BLUE[2] - OBSIDIAN[2]) * (1 - r/400) * 0.2)
        )
        draw.ellipse([400-r, 400-r, 400+r, 400+r], fill=color)

    # Modern Tech Mark (Larger)
    draw.rounded_rectangle([250, 250, 550, 550], radius=80, fill=NEURAL_BLUE)
    draw.ellipse([370, 370, 430, 430], fill=WHITE)
    
    img.save('twitter_pfp.png')
    print("✅ PFP Enhanced & Generated (800x800).")

def generate_cover():
    # 1500x500 Cover
    img = Image.new('RGB', (1500, 500), color=OBSIDIAN)
    draw = ImageDraw.Draw(img)
    
    # Subtle accent line
    draw.rectangle([0, 0, 1500, 10], fill=NEURAL_BLUE)
    
    # Text Placeholder (Center)
    draw.rectangle([600, 230, 900, 270], fill=NEURAL_BLUE)
    
    img.save('twitter_cover.png')
    print("✅ Cover Image Generated (Modern Tech).")

if __name__ == "__main__":
    generate_pfp()
    generate_cover()
