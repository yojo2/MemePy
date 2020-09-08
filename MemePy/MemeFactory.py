import shutil
from enum import Enum
from io import BytesIO

import requests
from PIL import Image, ImageDraw

from .MemeLibJsonDecoder import generate_standard_meme_dict
from .MemeModel import MemeImage

MemeLib = generate_standard_meme_dict()

def split_line(text, font, width):
    if len(text) > 200:
        raise ValueError("Text input must not be longer than 150 characters")
    text = text
    returntext = ""
    while text:
        if (font.getsize(text)[0]) < width:
            returntext += text
            break
        for i in range(len(text), 0, -1):
            if (font.getsize(text[:i])[0]) < width:
                if ' ' not in text[:i]:
                    returntext += text[:i] + "-\n"
                    text = text[i:]
                else:
                    for l in range(i, 0, -1):
                        if text[l] == ' ':
                            returntext += text[:l]
                            returntext += "\n"
                            text = text[l + 1:]
                            break
                break
    if len(returntext) > 3 and returntext[-3] == "-":
        returntext = returntext[:-3]
    return returntext


def get_textbox_margins(text, font, max_size, drawer):
    width_margin = round((max_size[0] - drawer.textsize(text, font)[0]) / 2)
    height_margin = round((max_size[1] - drawer.textsize(text, font)[1]) / 2)
    return width_margin, height_margin


def download_image(address):
    resp = requests.get(address, stream=True)
    file = BytesIO()
    resp.raw.decode_content = True
    shutil.copyfileobj(resp.raw, file)
    del resp
    return Image.open(file)


class TextType(Enum):
    Text = 0,
    Image = 1


class MemeOptions(Enum):
    Stretch = 0,


class MemeFactory:
    def __init__(self, meme_image:MemeImage, args):
        self.extract_options(args)
        self.meme_image = meme_image
        self.output_image = Image.open(meme_image.image_file_path)
        self.initial_dimensions = self.output_image.size
        if len(self.texts) < meme_image.count_non_optional():
            error_message = "Invalid arguments: Expected " + str(len(meme_image.text_zones)) + " arguments, but received " + str(len(self.texts)) + "."
            for t in self.texts:
                if t.startswith("{") and t.endswith("}"):
                    error_message += " Double check that the `options {...}` are spelt correctly"
                    break
            raise ValueError(error_message)
        self.apply_modification()


    @staticmethod
    def factory_from_template(template, args):
        try:
            for m in MemeLib:
                if template.lower() == m.lower():
                    return MemeFactory(MemeLib[m], args)
            raise ValueError("The meme template \"" + template + "\" does not exist")
        except Exception as e:
            raise e


    def apply_rotation(self, angle):
        self.output_image = self.output_image.rotate(angle, expand=True)


    def calculate_margins(self):
        return (
            (self.output_image.size[0] - self.initial_dimensions[0]) / 2,
            (self.output_image.size[1] - self.initial_dimensions[1]) / 2
        )


    def post_rotation_crop(self):
        (horizontal_margin, vertical_margin) = self.calculate_margins()
        self.output_image = self.output_image.crop((
            horizontal_margin,
            vertical_margin,
            horizontal_margin + self.initial_dimensions[0],
            vertical_margin + self.initial_dimensions[1]
        ))


    def apply_modification(self):
        drawer = ImageDraw.Draw(self.output_image)
        for i in range(len(self.meme_image.text_zones)):
            if i == len(self.texts):
                break

            zone = self.meme_image.text_zones[i]

            text_type = TextType.Text
            text_content = self.texts[i]

            if str.startswith(text_content, "<https://") and str.endswith(text_content, ">"):
                text_type = TextType.Image
            elif zone.all_caps:
                text_content = self.texts[i].upper()

            if zone.angle == 0:
                self.draw_text_zone(zone, text_content, text_type, drawer)
            else:
                self.apply_rotation(zone.angle)
                drawer = ImageDraw.Draw(self.output_image)
                self.draw_text_zone(zone, text_content, text_type, drawer)
                self.apply_rotation(-zone.angle)
                self.post_rotation_crop()


    def draw_text_zone(self, text_zone, text, text_type, drawer):
        if text_type == TextType.Text:
            self.draw_text(text_zone, text, drawer)
        else:
            self.draw_image(text_zone, text)


    def draw_image(self, text_zone, text):
        text = text[1:-1]
        img = download_image(text)
        img = self.resize_image(img, text_zone.dimensions)
        margins = get_centered_image_margins(img.size, text_zone.dimensions)
        pos = (
            text_zone.pos[0] + margins[0],
            text_zone.pos[1] + margins[1]
        )
        self.output_image.paste(img, pos, img.convert("RGBA"))


    def resize_image(self, img, text_zone_dimensions):
        resize_dimensions = get_scaled_dimensions(img, text_zone_dimensions)
        if self.options.__contains__(MemeOptions.Stretch):
            resize_dimensions = list(text_zone_dimensions)
        return img.resize(resize_dimensions, Image.ANTIALIAS)


    def extract_options(self, args):
        args = list(args)
        options = []
        for i in range(len(args)):
            for o in MemeOptions:
                if "{" + o.name.lower() + "}" == args[i].lower():
                    options.append(o)
                    args[i] = ""
        self.options = options
        self.texts = list(filter("".__ne__, args))


    @staticmethod
    def draw_text(text_zone, text, drawer):
        def draw_text_on_image(tz, t, d, sp, x, y, black):
            # 101 / 96 magic value calculated for 96px Impact, might be reasonable to change this to something more universal
            text_offset = round(tz.font_size * sp.count("\n") * 101 / 96) if tz.adjust_multiline else 0

            pos = (
                tz.pos[0]+x + margins[0],
                tz.pos[1]+y-text_offset + margins[1]
            )
            d.text(
                pos,
                sp,
                "black" if black else "white",
                tz.font,
                align="center"
            )
        
        split_text = split_line(text, text_zone.font, text_zone.dimensions[0])
        
        margins = list(get_textbox_margins(
            split_text,
            text_zone.font,
            text_zone.dimensions,
            drawer
        ))
        for i in range(2):
            if margins[i] < 0 or not text_zone.centering[i]:
                margins[i] = 0

        if text_zone.outline:
            # returns 1px outline for fonts < 32px, 3px outline for fonts >= 72px
            outline_offset = round((0.00001157407 * float(text_zone.font_size * text_zone.font_size)) + (0.02708333333 * text_zone.font_size) + 0.5)

            draw_text_on_image(text_zone, text, drawer, split_text, outline_offset, 0, not text_zone.black)
            draw_text_on_image(text_zone, text, drawer, split_text, -outline_offset, 0, not text_zone.black)
            draw_text_on_image(text_zone, text, drawer, split_text, 0, outline_offset, not text_zone.black)
            draw_text_on_image(text_zone, text, drawer, split_text, 0, -outline_offset, not text_zone.black)
        
        draw_text_on_image(text_zone, text, drawer, split_text, 0, 0, text_zone.black)



def get_centered_image_margins(current_dimensions, max_dimensions):
    return round((max_dimensions[0] - current_dimensions[0]) / 2), round((max_dimensions[1] - current_dimensions[1]) / 2)


def get_scaled_dimensions(img, text_zone_dimensions):
    image_aspect_ratio = img.size[0] / img.size[1]
    zone_aspect_ratio = text_zone_dimensions[0] / text_zone_dimensions[1]
    if image_aspect_ratio >= zone_aspect_ratio:
        return [text_zone_dimensions[0], round(text_zone_dimensions[0] / image_aspect_ratio)]
    else:
        return [round(text_zone_dimensions[1] * image_aspect_ratio), text_zone_dimensions[1]]

