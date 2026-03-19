from PIL import Image, ImageDraw, ImageFont
import os

# Create a new image with a dark scientific background
width, height = 800, 400
img = Image.new('RGB', (width, height), color='#1a1a2e')
draw = ImageDraw.Draw(img)

# Draw a circular atom-like design in the center
center_x, center_y = width // 2, height // 2
circle_radius = 80

# Outer circles (orbital paths)
for angle in range(0, 360, 30):
    x1 = center_x + int(circle_radius * 1.5 * 0.9)
    y1 = center_y + int(circle_radius * 0.5 * 0.5)
    x2 = center_x - int(circle_radius * 1.5 * 0.9)
    y2 = center_y - int(circle_radius * 0.5 * 0.5)
    draw.ellipse([x1-5, y1-5, x1+5, y1+5], fill='#00d4ff')

# Main circle (Einstein head silhouette)
draw.ellipse([
    center_x - circle_radius,
    center_y - circle_radius,
    center_x + circle_radius,
    center_y + circle_radius
], outline='#00d4ff', width=4)

# Add inner glow
draw.ellipse([
    center_x - circle_radius + 10,
    center_y - circle_radius + 10,
    center_x + circle_radius - 10,
    center_y + circle_radius - 10
], outline='#4ecdc4', width=2)

# Draw atomic orbiting lines
draw.arc([
    center_x - circle_radius - 20,
    center_y - circle_radius - 20,
    center_x + circle_radius + 20,
    center_y + circle_radius + 20
], start=0, end=180, fill='#00d4ff', width=2)

draw.arc([
    center_x - circle_radius - 30,
    center_y - 20,
    center_x + circle_radius + 30,
    center_y + circle_radius + 20
], start=180, end=360, fill='#4ecdc4', width=2)

# Try to use a nice font, fall back to default if not available
try:
    # Try system fonts
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        try:
            title_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 48)
            subtitle_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
except:
    title_font = ImageFont.load_default()
    subtitle_font = ImageFont.load_default()

# Add text
title_text = "Einstein Bot"
subtitle_text = "AI-Powered Universal Assistant"

# Get text bbox for centering
title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)

title_width = title_bbox[2] - title_bbox[0]
subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]

# Draw title on the left
draw.text((50, center_y - 40), title_text, font=title_font, fill='#ffffff')
draw.text((50, center_y + 20), subtitle_text, font=subtitle_font, fill='#aaaaaa')

# Draw decorative elements
draw.line([(20, 50), (20, height-50)], fill='#00d4ff', width=2)
draw.line([(width-20, 50), (width-20, height-50)], fill='#00d4ff', width=2)

# Add scientific symbols
draw.text((width - 150, 80), "⚛", font=title_font, fill='#4ecdc4')
draw.text((width - 100, 300), "🧠", font=subtitle_font, fill='#00d4ff')

# Save the image
assets_dir = r"D:\clow bot main\clow bot\Einstein-Bot-\assets"
os.makedirs(assets_dir, exist_ok=True)
img.save(os.path.join(assets_dir, 'logo.png'))
print(f"Logo created at: {os.path.join(assets_dir, 'logo.png')}")

# Also create a smaller banner version
banner_width, banner_height = 1200, 300
banner = Image.new('RGB', (banner_width, banner_height), color='#1a1a2e')
draw_banner = ImageDraw.Draw(banner)

# Draw gradient-like background with lines
for i in range(0, banner_width, 20):
    alpha = int(255 * (1 - i / banner_width))
    draw_banner.line([(i, 0), (i, banner_height)], fill=(26, 26, 46))

# Draw the atom design on the right
banner_center_x = banner_width - 150
banner_center_y = banner_height // 2
draw_banner.ellipse([
    banner_center_x - 60,
    banner_center_y - 60,
    banner_center_x + 60,
    banner_center_y + 60
], outline='#00d4ff', width=3)

# Text on the left
try:
    banner_title_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 60)
    banner_sub_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 28)
except:
    banner_title_font = ImageFont.load_default()
    banner_sub_font = ImageFont.load_default()

draw_banner.text((50, 80), "Einstein Bot", font=banner_title_font, fill='#ffffff')
draw_banner.text((50, 160), "AI-Powered Telegram Bot • Video Downloader • File Manager", font=banner_sub_font, fill='#aaaaaa')

# Decorative line
draw_banner.line([(50, 220), (500, 220)], fill='#00d4ff', width=3)

banner.save(os.path.join(assets_dir, 'banner.png'))
print(f"Banner created at: {os.path.join(assets_dir, 'banner.png')}")
