from PIL import Image, ImageDraw
import sys
import json

json_path = sys.argv[1]
x_size = 1920
y_size = 1080

# background
img = Image.new('RGBA', (x_size, y_size), 'white')

# foregroup
tmp = Image.new('RGBA', img.size, 'white')
draw = ImageDraw.Draw(tmp)
with open(json_path) as json_file:
    # draw rectangles as given by points
    data = json.load(json_file)
    for entry in data:
        line = []
        for point in entry["points"]:
            line.append((int(point["x"]*x_size), int(point["y"]*y_size)))
        draw.polygon(line, fill=(128, 128, 128, 230))

# merge images
img = Image.alpha_composite(img, tmp)
img.save(json_path + ".png", "PNG")