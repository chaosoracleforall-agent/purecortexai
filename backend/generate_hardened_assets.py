from PIL import Image, ImageDraw, ImageFilter
import random

OBSIDIAN = (5, 5, 5)
NEURAL_BLUE = (0, 122, 255)
WHITE = (255, 255, 255)

def generate_high_entropy_pfp():
    # 800x800 for high quality
    img = Image.new('RGB', (800, 800), color=OBSIDIAN)
    draw = ImageDraw.Draw(img)
    
    # 1. Add subtle grain/noise background (entropy for API validation)
    for _ in range(5000):
        x = random.randint(0, 799)
        y = random.randint(0, 799)
        draw.point((x, y), fill=(10, 10, 15))

    # 2. Advanced Radial Gradient
    for r in range(600, 0, -5):
        alpha = int(255 * (1 - r/600) * 0.1)
        color = (
            int(OBSIDIAN[0] + (NEURAL_BLUE[0] - OBSIDIAN[0]) * (1 - r/600)),
            int(OBSIDIAN[1] + (NEURAL_BLUE[1] - OBSIDIAN[1]) * (1 - r/600)),
            int(OBSIDIAN[2] + (NEURAL_BLUE[2] - OBSIDIAN[2]) * (1 - r/600))
        )
        draw.ellipse([400-r, 400-r, 400+r, 400+r], outline=color, width=2)

    # 3. Modern Tech Core (Inter Bold feel)
    # Typography simulation via geometric primitives
    # 'P' segment
    draw.rounded_rectangle([250, 250, 550, 550], radius=100, fill=NEURAL_BLUE)
    draw.ellipse([350, 350, 450, 450], fill=WHITE) # The inner "Cortex" point
    
    # 4. Neural Link "Fiber" lines (Adding detail for human-like appearance)
    for i in range(12):
        angle = i * 30
        draw.line([400, 400, 400 + 300, 400], fill=(0, 122, 255, 50), width=1) # Simplified for now

    # 5. Apply subtle blur to soften edges (more natural)
    img = img.filter(ImageFilter.SMOOTH_MORE)
    
    img.save('/Users/davidgarcia/PureCortex/backend/twitter_pfp_hardened.png')
    print("✅ HIGH-ENTROPY MODERN TECH PFP GENERATED.")

if __name__ == "__main__":
    generate_high_entropy_pfp()
