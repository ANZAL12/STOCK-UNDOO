from PIL import Image
import os

src_path = r"C:\Users\USER\.gemini\antigravity\brain\914043d1-211b-451e-9017-252c78191558\.user_uploaded\media_1794145629273_81604944.jpg"
im = Image.open(src_path)
width, height = im.size
print(f"Image size: {width}x{height}")

# Save full logo
im.save(r"a:\Stock Undoo\branding\logo_original.jpg")
im.save(r"a:\Stock Undoo\frontend\public\logo_original.jpg")

# The icon (SU + box + arrow) is located roughly in the top 75% of the image.
# Let's crop the emblem precisely:
# In a 1024x1024 image, the emblem is in y: 200 to 680, x: 200 to 820.
# Let's find bounding box of non-white pixels:
gray = im.convert('L')
# Invert so black is high
from PIL import ImageOps
inv = ImageOps.invert(gray)
# Threshold to remove slight JPEG noise
inv = inv.point(lambda p: 255 if p > 30 else 0)
bbox = inv.getbbox()
print(f"Full content bbox: {bbox}")

# The text "Stock Undo" is at the bottom. Let's find where the gap between emblem and text is.
# Crop the emblem only:
# Looking at the image, text is around the bottom 25%.
# Let's crop just the emblem:
emblem_box = (bbox[0], bbox[1], bbox[2], int(bbox[1] + (bbox[3] - bbox[1]) * 0.76))
emblem_inv = inv.crop(emblem_box)
emblem_tight = emblem_inv.getbbox()
actual_emblem_box = (
    bbox[0] + emblem_tight[0] - 10,
    bbox[1] + emblem_tight[1] - 10,
    bbox[0] + emblem_tight[2] + 10,
    bbox[1] + emblem_tight[3] + 10
)
emblem = im.crop(actual_emblem_box)
print(f"Emblem crop size: {emblem.size}")

# Make white background transparent for clean display
emblem_rgba = emblem.convert("RGBA")
datas = emblem_rgba.getdata()
new_data = []
for item in datas:
    # If pixel is close to white (R,G,B > 240)
    if item[0] > 240 and item[1] > 240 and item[2] > 240:
        new_data.append((255, 255, 255, 0)) # transparent
    else:
        new_data.append(item)
emblem_rgba.putdata(new_data)

emblem_rgba.save(r"a:\Stock Undoo\branding\su_icon.png")
emblem_rgba.save(r"a:\Stock Undoo\frontend\public\su_icon.png")
emblem_rgba.save(r"a:\Stock Undoo\frontend\public\logo.png")
emblem.save(r"a:\Stock Undoo\frontend\public\su_icon_white_bg.png")

print("Successfully generated su_icon.png and logo assets!")

