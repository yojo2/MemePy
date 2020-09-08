class TextZone:
    def __init__(self, pos, dimensions, font, angle=0, text_color=(0,0,0), centering=(False, False), optional=False, font_size=24, black=False, outline=True, all_caps=False, adjust_multiline=False):
        self.pos = pos
        self.dimensions = dimensions
        self.font = font
        self.angle = angle
        self.text_color = text_color
        self.centering = centering
        self.optional = optional
        self.font_size = font_size
        self.black = black
        self.outline = outline
        self.all_caps = all_caps
        self.adjust_multiline = adjust_multiline

class MemeImage:
    def __init__(self, image_file_path, text_zones):
        self.image_file_path = image_file_path
        self.text_zones = text_zones

    def count_non_optional(self):
        count = 0
        for z in self.text_zones:
            if not z.optional:
                count += 1
        return count
