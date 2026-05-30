from PIL import Image, ImageDraw, ImageFont
import os

def create_text_image():
    # Create a new image with white background
    width, height = 800, 200
    image = Image.new('RGBA', (width, height), color='white')
    
    # Create a drawing context
    draw = ImageDraw.Draw(image)
    
    # Text to be rendered
    text = "Absolutely crazy! 🔥😵😂"
    
    # Load the specified Roboto Condensed Black font
    font_size = 50
    text_font_path = "./fonts/Roboto_Condensed-Black.ttf"
    
    try:
        text_font = ImageFont.truetype(text_font_path, font_size)
        print(f"Loaded font: {text_font_path}")
    except Exception as e:
        text_font = ImageFont.load_default()
        print(f"Error loading font {text_font_path}: {e}. Using default font.")
    
    # Try to find an emoji font for colorful emojis
    emoji_font = None
    emoji_font_paths = [
        # Windows
        "C:/Windows/Fonts/seguiemj.ttf",  # Segoe UI Emoji
    ]
    
    for emoji_path in emoji_font_paths:
        if os.path.exists(emoji_path):
            try:
                emoji_font = ImageFont.truetype(emoji_path, font_size)
                print(f"Loaded emoji font: {emoji_path}")
                break
            except:
                continue
    
    if emoji_font is None:
        emoji_font = text_font
        print("No emoji font found, using text font for emojis")
    
    # Split text into text and emoji parts
    text_part = "Absolutely crazy! "
    emoji_part = "🔥😵😂"
    
    # Calculate positions for text and emojis
    text_bbox = draw.textbbox((0, 0), text_part, font=text_font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    emoji_bbox = draw.textbbox((0, 0), emoji_part, font=emoji_font)
    emoji_width = emoji_bbox[2] - emoji_bbox[0]
    emoji_height = emoji_bbox[3] - emoji_bbox[1]
    
    total_width = text_width + emoji_width
    max_height = max(text_height, emoji_height)
    
    # Center the combined text and emojis
    start_x = (width - total_width) // 2
    text_y = (height - max_height) // 2
    
    # Draw the text part
    draw.text((start_x, text_y), text_part, font=text_font, fill='black')
    
    # Draw the emoji part
    emoji_x = start_x + text_width
    draw.text((emoji_x, text_y+10), emoji_part, font=emoji_font, fill='black', embedded_color=True)
    
    # Save the image
    output_filename = 'crazy_text.png'
    image.save(output_filename)
    print(f"Image saved as '{output_filename}'")
    
    return image

if __name__ == "__main__":
    create_text_image()