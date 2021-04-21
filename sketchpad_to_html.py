from libopensesame.sketchpad_elements import *

# TODO: use context to translate vars

class SketchpadTranslator:
    def __init__(self, _context, _elements):
        self.html = '<canvas id="sketchpad"></canvas>'
        self.context = _context
        self.elements = _elements

    def to_js(self):
        code = """\
const canvas = document.getElementById("sketchpad");
const ctx = canvas.getContext("2d");
// defaults
ctx.textAlign = "center";
ctx.textBaseline = "middle";
"""
        for el in self.elements:
            if isinstance(el, arrow):
                code += self.draw_arrow(el)
            elif isinstance(el, circle):
                code += self.draw_circle(el)
            elif isinstance(el, ellipse):
                code += self.draw_ellipse(el)
            elif isinstance(el, fixdot):
                code += self.draw_fixdot(el)
            elif isinstance(el, gabor):
                code += self.draw_gabor(el)
            elif isinstance(el, image):
                code += self.draw_image(el)
            elif isinstance(el, line):
                code += self.draw_line(el)
            elif isinstance(el, noise):
                code += self.draw_noise(el)
            elif isinstance(el, rect):
                code += self.draw_rect(el)
            elif isinstance(el, textline):
                code += self.draw_textline(el)
            else:
                raise Exception(f"Unknown element type: {repr(type(el))}")
        return code, self.html

    def set_colour(self, col):
        return 'ctx.strokeStyle = "{col}";\n';

    def set_width(self, w):
        return 'ctx.lineWidth = {w};\n'

    def set_size_and_font(self, size, font):
        # TODO: stack up fonts we need to retrieve from Google Fonts
        # (or similar, or self-hosted)
        return 'ctx.font = "{size}px {font}";\n'

    def draw_rect(self, rect):
        code = self.set_colour(rect.color) + self.set_width(rect.penwidth)
        if rect.fill:
            verb = "fill"
        else:
            verb = "stroke"
        code += "ctx.{verb}Rect({rect.x},{rect.y},{rect.w},{rect.h})"
        return code

    def draw_line(self, line):
        code = self.set_colour(line.color) + self.set_width(line.penwidth)
        code += self.draw_polyline([(line.x1, line.y1), (line.x2, line.y2)])
        return code

    def draw_textline(self, textline):
        props = textline.properties
        code = (
            self.set_colour(props["color"]) +
            self.set_size_and_font(props["font_size"], props["font_family"])
        )
        code += 'ctx.fillText("{textline.text}");'
        return code

    def draw_polyline(self, pts, close=False, fill=False):
        if len(coords == 0):
            return ""
        code = "ctx.beginPath();\n"
        code += "ctx.moveTo({pts[0][0]},{pts[0][1]});\n"
        code += "\n".join(
            'ctx.lineTo({pts[idx][0]},{pts[idx][1]});'
            for idx in range(1,len(coords))
        )
        if close:
            # back to the start
            code += 'ctx.lineTo({pts[0][0]},pts[0][1]);\n'
        code += 'ctx.closePath();'
        if fill:
            code += 'ctx.fill();'
        else:
            code += 'ctx.stroke();'
        return code
