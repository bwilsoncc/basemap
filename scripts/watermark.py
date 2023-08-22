"""
    Prints text onto an image file.

    This is used to put text blocks onto thumbnails used in ArcGIS Portal.
    It will accept any image size but Esri recommands 600x400 so it's optimized
    for that. In the UI they are shrunken to 200x133.

    I guess it's not a watermark at all since this version is opaque.

    This version does a textmark and a caption.
    The "textmark" is the string that goes on the right
    and the "coption" goes on the bottom.

    FIXME: colors are hardcoded.
    
    FIXME: fonts and font sizes are hardcoded in, and probably need to be 
    adjusted whenever you switch fonts or image sizes.
    That is why I settled on using 600x400 images as the standard.

    FIXME: likewise, the dimensions of the textboxes are hardcoded in.
"""
import os
from PIL import Image, ImageColor, ImageFont, ImageDraw

SYSTEMFONTS = 'C:/Windows/Fonts/'

COUNTY_TEXTBAR_COLOR = "rgb( 65%, 83%, 91%)" # pale blue
BLACK = "rgb(0, 0, 0)" # opaque inky black
WHITE = "rgb(100%, 100%, 100%)"

COUNTY_BACKGROUND_COLOR = "rgb( 42%, 57%, 80%)" # darker blue
COUNTY_BORDER_COLOR = "rgb(97%, 92%, 38%)" # yellow and opaque 

CAPTION_FONTSIZE = 40
TEXTBAR_FONTSIZE = 30


def get_target(output_name):
    """ 
        Find an unused output file name.
    """
    output_folder, output_file = os.path.split(output_name)
    file, extn = os.path.splitext(output_file)
#    extn = ".png" # Force all output into PNG format because it supports alpha

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
    
        Returns the actual output name
    """
    (path, filename) = os.path.split(input_name)

    base = Image.open(input_name).convert('RGBA')
    xmax, ymax = base.size
    tl_xmax = xmax

    if textmark:
    # == textmark goes sideways on the right ==
        font = ImageFont.truetype(SYSTEMFONTS + fontname, TEXTBAR_FONTSIZE)

        # find text image size
        # Remember output box is rotated 90 degrees
        bbox = font.getbbox(caption)

        tm_xmax = ymax # full height
        tm_ymax = min(TEXTBAR_FONTSIZE+10, xmax)
        tl_xmax = xmax - tm_ymax

        box_color = COUNTY_BACKGROUND_COLOR
        text_color = WHITE

        tm = Image.new("RGB", [tm_xmax,tm_ymax])
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
        font = ImageFont.truetype(SYSTEMFONTS + fontname, CAPTION_FONTSIZE)
        box_color = COUNTY_TEXTBAR_COLOR
        tl_color  = BLACK

        tl_ymax = min(CAPTION_FONTSIZE+10, ymax)
        
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
    from scripts.config import Config

    # Collect the information we'll put in a comment string.
    cwd,scriptname = os.path.split(__file__)
    datestamp = datetime.now().strftime("%m/%d/%Y %H:%M")
    caption = "This is the caption"
    textmark = datestamp
    scratch_workspace = "C:\\TEMP"

    # Choose one,
    # pull everything from your Pictures folder...
    #srcdir = os.path.join(os.environ.get('USERPROFILE'), "Pictures")
    # or from this project's test files.
    srcdir = os.path.join("assets/")

    myfont = "FREESCPT.ttf" # pick something from your fonts
    for item in ['package_thumbnail.png', 'clatsopcounty_thumbnail.png', 'roads_thumbnail.png']: # os.listdir(srcdir):

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

            # Maybe I want output in PNG format
            f,e = os.path.splitext(file)
            file = f + '.png'

            output_name = os.path.join(scratch_workspace, file)
            outfile = mark(imgfile, output_name, caption, textmark, fontname=myfont)
            print(outfile)
        except Exception as e:
            print("Failed!", e)

# That's all!
