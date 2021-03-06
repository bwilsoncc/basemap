"""
    Prints text onto an image file.

    This version does a textmark and a caption.
    The "textmark" is the string that goes on the right
    and the coption goes on the bottom.

    FIXME: font sizes are hardcoded in, and probably need to be 
    adjusted whenever you switch fonts.

    FIXME: likewise, the dimensions of the textboxes are hardcoded in.
"""
import os
from PIL import Image, ImageFont, ImageDraw
from colors import find_dominant_colors

SYSTEMFONTS = 'C:/Windows/Fonts/'

COUNTY_BACKGROUND_COLOR = ( 62, 125, 135, 255) # county greenish color
COUNTY_TEXT_COLOR = (255, 255, 255, 255) # white

def get_target(output_name):
    """ 
        Find an unused output file name.
    """
    output_folder, output_file = os.path.split(output_name)
    file, extn = os.path.splitext(output_file)
    extn = ".png" # Force all output into PNG format because it supports alpha

    outfile = output_name
    n = 1
    while os.path.exists(outfile):
        # Keep adding 1 until we hit an unused name!
        outfile = os.path.join(output_folder, file + "(%s)" % n + extn)
        n += 1
    return outfile


def mark(input_name, output_name, caption="", textmark="", fontname="arial.ttf"):
    """ 
        Print the strings in "caption" and "textmark" onto a copy of input_image. 
        Writes the new image to "output_name".
        The name of the output file will be the same unless there's already a file there
        in which case it does the numbered suffix thing (eg "myfile.jpg" -> "myfile(3).jpg")
    """
    (path, filename) = os.path.split(input_name)

    base = Image.open(input_name).convert('RGBA')
    xmax, ymax = base.size
    tl_xmax = xmax

    if textmark:
    # == textmark goes sideways on the right ==
        font = ImageFont.truetype(SYSTEMFONTS + fontname, 18)

        # find text image size
        # Remember output box is rotated 90 degrees
        bbox = font.getbbox(caption)

        tm_xmax = ymax # full height
        tm_ymax = min(30, xmax)
        tl_xmax = xmax - tm_ymax

        # find a suitable background color 
        (box_color, text_color) = find_dominant_colors(input_name)

        tm = Image.new("RGBA", [tm_xmax,tm_ymax])
        d = ImageDraw.Draw(tm)

        # make a filled rectangle in the correct colors
        d.rectangle([0,0, tm_xmax,tm_ymax], 
            fill=box_color, outline=None, width=1)
        d.text((tm_xmax/2+2,tm_ymax/2), anchor='mm', 
            text=textmark, fill=text_color, font=font)
        twisted = tm.transpose(Image.ROTATE_90)

        # Upper left corner for the textmark
        dest = (xmax - tm_ymax, 0)
        base.paste(twisted, box=dest)

    if caption:
    # == caption goes across the bottom
        font = ImageFont.truetype(SYSTEMFONTS + fontname, 20)
        box_color = COUNTY_BACKGROUND_COLOR
        tl_color  = COUNTY_TEXT_COLOR

        tl_ymax = min(30, ymax)
        
        tl = Image.new("RGBA", [tl_xmax,tl_ymax])
        d = ImageDraw.Draw(tl)

        # make a filled rectangle in the correct colors
        d.rectangle([0,0, tl_xmax,tl_ymax], fill=box_color, outline=None, width=1)
        d.text((tl_xmax/2,tl_ymax/2), anchor="mm", 
            text=caption, fill=tl_color, font=font)

        dest = (0, ymax-tl_ymax)
        base.paste(tl, box=dest)

    # Don't overwrite an existing file.
    outfile = get_target(output_name)
    base.save(outfile)
    return outfile


if __name__ == "__main__":
    # This is unit test code
    #
    # It pulls all images from your "pictures" folder and watermarks them
    # It makes copies into C:\TEMP so the originals are unchanged.

    from datetime import datetime
    from config import Config

    # Collect the information we'll put in a comment string.
    cwd,scriptname = os.path.split(__file__)
    datestamp = datetime.now().strftime("%Y%m%d %H%M")
    caption = "This is the caption"
    textmark = datestamp
    scratch_workspace = "C:\\TEMP"

    # Choose one,
    # pull everything from your Pictures folder...
    srcdir = os.path.join(os.environ.get('USERPROFILE'), "Pictures")
    # or from this project's test files.
    #srcdir = os.path.join("k:/webmaps/basemap/assets/")

    myfont = "BROADW.TTF" # pick something from your fonts
    for item in os.listdir(srcdir):
        print(item)
        imgfile = os.path.join(srcdir, item)

        try:
            # It's possible to test to see if the image is an animated GIF
            # or tiny but not necessary as
            # we just catch these problems as exceptions here.
#            base = Image.open(input_name)
#            xmax, ymax = base.size
#            if ymax < 20: return
#            if base.is_animated:
#                return
            path,file = os.path.split(imgfile)
            output_name = os.path.join(scratch_workspace, file)
            outfile = mark(imgfile, output_name, caption, textmark, fontname=myfont)
            print(outfile)
        except Exception as e:
            print("Failed!", e)

# That's all!
