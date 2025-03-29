import json
from PIL import Image
import os
import math

working_dir = "./"
valid_extensions = [".jpg", ".png"]

images = []
for filename in os.listdir(working_dir):
    f = os.path.join(working_dir, filename)
    if os.path.isfile(f):
        filename, file_extension = os.path.splitext(f)
        if file_extension.lower() in valid_extensions:
            images.append(f)
            print(filename, file_extension)

for file_path in images:
    image = Image.open(file_path)
    image = image.convert("RGB")
    width, height = image.size
    pixels = []

    # Loop over each pixel and get hex color value
    '''
    for y in range(height):
        for x in range(width):
            r, g, b = image.getpixel((x, y))
            hex_value = f"#{r:02x}{g:02x}{b:02x}"
            pixels.append(hex_value)
    '''
    for skåp_x in range(round(width/5)):
        for skåp_y in range(round(height/12)):
            for row in range(12):
                for column in range(5):
                    x = (skåp_x * 5) + column
                    y = (skåp_y * 12) + row
                    r, g, b = image.getpixel((x, y))
                    hex_value = f"#{r:02x}{g:02x}{b:02x}"
                    pixels.append(hex_value)

    data = {
        "width": width,
        "height": height,
        "pixels": pixels
    }

    filename, file_extension = os.path.splitext(file_path)
    with open(f"{filename}.json", "w") as f:
        json.dump(data, f, indent=4, sort_keys=True)