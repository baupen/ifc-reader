from PIL import Image, ImageDraw
import sys
import json

json_path = sys.argv[1]

img = Image.new('RGB', (1920, 1080), 'white')

draw = ImageDraw.Draw(img)

with open(json_path) as json_file:
    data = json.load(json_file)
    for entry in data:
        
        draw.line((0, 0) + im.size, fill=128)
        draw.line((0, im.size[1], im.size[0], 0), fill=128)

img.save(json_path + ".png", "PNG")