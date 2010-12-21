#
# vim: ts=4 sw=4 expandtab ai:
#
# Copyright (C) 2008-2010 Exposong.org
#
# ExpoSong is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Themes define the layout of a presentation screen.

The points will be based on percentages (0.0 - 1.0) to be compatible with all
screen sizes. Colors can be anything parsable by gtk.gdk.color_parse()
[http://library.gnome.org/devel/pygtk/stable/class-gdkcolor.html#function-gdk--color-parse].

Themes will support a flexible background layout system. Images, gradiants, and
solid colors can be set for set region. Background images will be stored in
DATA_PATH/themes/bg.

Shadow offsets are measure in percentage of font height. So an offset of 0.5
for point 12 font is 6 points.

Margins are measured in Pixels.
"""

import cairo
import gobject
import gtk
import gtk.gdk
import math
import operator
import os.path
import pango
from gtk.gdk import pixbuf_new_from_file as pb_new
from xml.etree import cElementTree as etree

from exposong import DATA_PATH

LEFT = pango.ALIGN_LEFT
CENTER = pango.ALIGN_CENTER
RIGHT = pango.ALIGN_RIGHT
TOP = -1
MIDDLE = 0
BOTTOM = 1

ASPECT_FIT = 1
ASPECT_FILL = 2

class Theme(object):
    """
    A theme item.
    """
    def __init__(self, filename=None):
        "Create a theme."
        self.filename = filename
        self.backgrounds = []
        self.footer = None
        self.body = None
        if filename:
            tree = etree.parse(filename)
            self.load(tree)
    
    def get_footer_pos(self):
        "Return the position where the footer begins."
        if self.footer:
            return self.footer.pos[1]
        return 0.85
    
    def get_footer(self):
        return self.footer

    def get_body(self):
        return self.body
    
    def load(self, tree):
        "Load the theme from an XML file."
        if isinstance(tree, etree.ElementTree):
            root = tree.getroot()
        else:
            root = tree
        backgrounds = root.find(u'background')
        for bg in backgrounds.getchildren():
            bgobj = _Background.create_element(bg)
            if bgobj:
                self.backgrounds.append(bgobj)
        body = root.find(u'sections/body')
        if body:
            self.body = Section.from_xml(body)
        foot = root.find(u'sections/footer')
        if foot:
            self.footer = Section.from_xml(foot)
    
    def save(self):
        "Save theme to disk."
        pass
    
    def render(self, ccontext, bounds, slide):
        "Render the theme to the screen."
        self.render_color(ccontext, bounds, '#000')
        for bg in self.backgrounds:
            bg.draw(ccontext, bounds)
        if slide:
            for t in slide.get_body():
                t.draw(ccontext, bounds, self.body)
            for t in slide.get_footer():
                t.draw(ccontext, bounds, self.footer)
    
    @classmethod
    def render_color(cls, ccontext, bounds, color):
        "Render a solid color on the screen."
        clr = gtk.gdk.color_parse(color)
        solid = cairo.SolidPattern(clr.red / 65535.0, clr.green / 65535.0,
                                   clr.blue / 65535.0)
        if len(bounds) == 2:
            ccontext.rectangle(0, 0, *bounds)
        elif len(bounds) == 4:
            ccontext.rectangle(*bounds)
        else:
            raise Exception("`bounds` must have 2 or 4 arguments.")
        ccontext.set_source(solid)
        ccontext.fill()


class _Renderable(object):
    """
    An abstract class for a drawing element.
    
    pos:    This is the position on the screen (0.0, 1.0).
            Example: [0.0, 1.0, 0.8, 1.0]
    rpos:   This is the real position on the screen (actual points).
            Example: [0, 800, 800, 1000]
    """
    def __init__(self, pos=None):
        ""
        if isinstance(pos, list) and len(pos) == 4:
            self.pos = pos
        else:
            self.pos = [0.0, 0.0, 1.0, 1.0]
    
    def parse_xml(self, el):
        "Defines variables based on XML values."
        self.pos = [float(el.get('x1', 0.0)), float(el.get('y1', 0.0)),
                    float(el.get('x2', 1.0)), float(el.get('y2', 1.0))]
    
    def draw(self, ccontext, bounds):
        "Render the background to the context."
        if len(bounds) == 2:
            self.rpos = map(_product, bounds*2, self.pos)
        elif len(bounds) == 4:
            self.rpos = map(_product, bounds[-2:]*2, self.pos)
            self.rpos[0] += bounds[0]
            self.rpos[1] += bounds[1]
            self.rpos[2] += bounds[0]
            self.rpos[3] += bounds[1]
        else:
            raise Exception("`bounds` must have 2 or 4 elements")


class _Element(object):
    """
    An element in the XML.
    """
    
    @classmethod
    def create_element(cls, el):
        ""
        for c in cls.__subclasses__():
            if c.get_tag() == el.tag:
                return c.from_xml(el)
        return None
    
    @classmethod
    def from_xml(cls, el):
        "Creates an element"
        c = cls()
        c.parse_xml(el)
        return c
    
    @staticmethod
    def get_tag():
        ""
        return NotImplemented


class _Background(_Element):
    """
    A background object in the theme.
    """
    pass

class ColorBackground(_Background, _Renderable):
    """
    A solid color background.
    """
    def __init__(self, color="#fff", alpha=1.0, pos=None):
        ""
        _Renderable.__init__(self, pos)
        self.color = color
        self.alpha = alpha
    
    def parse_xml(self, el):
        "Defines variables based on XML values."
        _Renderable.parse_xml(self, el)
        self.color = el.get('color', "#fff")
        self.alpha = float(el.get('alpha', 1.0))
    
    def draw(self, ccontext, bounds):
        "Render the background to the context."
        _Renderable.draw(self, ccontext, bounds)
        
        color = gtk.gdk.color_parse(self.color)
        solid = cairo.SolidPattern(color.red / 65535.0, color.green / 65535.0,
                                   color.blue / 65535.0, self.alpha)
        ccontext.rectangle(*self.rpos[:2] +
                           map(_subtract, self.rpos[2:4], self.rpos[:2]))
        ccontext.set_source(solid)
        ccontext.fill()
    
    @staticmethod
    def get_tag():
        ""
        return "solid"


class GradiantBackground(_Background, _Renderable):
    """
    A gradiant background.
    """
    def __init__(self, angle=0, pos=None):
        ""
        _Renderable.__init__(self, pos)
        self.angle = None
        self.stops = []
    
    def parse_xml(self, el):
        "Defines variables based on XML values."
        _Renderable.parse_xml(self, el)
        self.angle = float(el.get('angle', 0))
        
        self.stops = []
        for pt in el.getchildren():
            assert pt.tag == 'point'
            stop = GradiantStop(float(pt.get("stop", 0.0)),
                                pt.get("color", "#fff"),
                                float(pt.get("alpha", 1.0)))
            self.stops.append(stop)
    
    def draw(self, ccontext, bounds):
        "Render the background to the context."
        _Renderable.draw(self, ccontext, bounds)
        
        # Compute the offset of the angle
        cent = [self.rpos[0] / 2 + self.rpos[2] / 2,
                self.rpos[3] / 2 + self.rpos[1] / 2]
        diff = [abs(self.rpos[0] - self.rpos[2])/2,
                abs(self.rpos[1] - self.rpos[3])/2]
        offset = [0, 0]
        angle = self.angle * 2 * math.pi / 360
        if (self.angle + 90) % 360 < 180:
            offset[1] = diff[1]
        else:
            offset[1] = -diff[1]
        offset[0] = offset[1] * math.tan(angle)
        if abs(offset[0]) > diff[0]:
            if self.angle % 360 < 180:
                offset[0] = diff[0]
            else:
                offset[0] = -diff[0]
            offset[1] = offset[0] / math.tan(angle)
        
        gradient = cairo.LinearGradient(*map(_subtract, cent, offset) +
                                        map(_add, cent, offset))
        for stop in self.stops:
            clr = gtk.gdk.color_parse(stop.color)
            gradient.add_color_stop_rgba(stop.location, clr.red / 65535.0,
                                        clr.green / 65535.0, clr.blue / 65535.0,
                                        stop.alpha)
        ccontext.rectangle(*self.rpos[:2] +
                           map(_subtract, self.rpos[2:4], self.rpos[:2]))
        ccontext.set_source(gradient)
        ccontext.fill()
    
    @staticmethod
    def get_tag():
        ""
        return "gradiant"


class GradiantStop(_Element):
    """
    A location with a color in a gradiant background.
    """
    def __init__(self, location=None, color=None, alpha=1.0):
        ""
        self.location = location
        self.color = color
        self.alpha = alpha


class ImageBackground(_Background, _Renderable):
    """
    An image background.
    """
    def __init__(self, src=None, pos=None, aspect=ASPECT_FILL):
        ""
        _Renderable.__init__(self, pos)
        self.src = src
        self.aspect = aspect
        self._original = None
        self._cache = {}
    
    def parse_xml(self, el):
        "Defines variables based on XML values."
        _Renderable.parse_xml(self, el)
        self.src = el.get('src')
        if el.get('aspect', 'fill') == 'fill':
            self.aspect = ASPECT_FILL
        elif el.get('aspect') == 'fit':
            self.aspect = ASPECT_FIT
        else:
            self.aspect = ASPECT_FILL
    
    def load(self, size):
        ""
        if not self._original:
            try:
                self._original = pb_new(os.path.join(DATA_PATH,'theme',
                                             'res', self.src))
            except gobject.GError:
                exposong.log.error('Could not find "%s".', self.src)
                return False
        
        size[:] = get_size(self._original, size, self.aspect)
        skey = 'x'.join(map(str, size))
        if skey not in self._cache:
            self._cache[skey] = scale_image(self._original, size, self.aspect)
        return self._cache[skey]
    
    def draw(self, ccontext, bounds):
        "Render the background to the context."
        _Renderable.draw(self, ccontext, bounds)
        
        #ccontext.rectangle(*self.rpos[:2] +
        #                   map(_subtract, self.rpos[2:4], self.rpos[:2]))
        size = map(_subtract, self.rpos[2:4], self.rpos[:2])
        
        img = self.load(size)
        pos = [(self.rpos[0] + self.rpos[2] - size[0])/2,
               (self.rpos[1] + self.rpos[3] - size[1])/2]
        if img:
            ccontext.set_source_pixbuf(img, *pos)
            ccontext.paint()
    
    @staticmethod
    def get_tag():
        ""
        return "img"

class Section(_Element):
    """
    A part of the screen with text.
    
    type_:  Can currently be one of "body" or "footer".
    """
    def __init__(self, type_=None, font="Sans 24", color="#fff",
                 shadow_color="#000", shadow_opacity=0.4, shadow_offset=None,
                 pos=None):
        _Element.__init__(self)
        if isinstance(pos, list) and len(pos) == 4:
            self.pos = pos
        else:
            self.pos = [0.0, 1.0, 0.0, 1.0]
        self.type_ = type_
        self.font = font
        self.color = color
        self.shadow_color = shadow_color
        self.shadow_opacity = shadow_opacity
        if shadow_offset:
            self.shadow_offset = shadow_offset
        else:
            self.shadow_offset = [0.1, 0.1]
    
    def parse_xml(self, el):
        "Defines variables based on XML values."
        self.type_ = el.tag
        self.pos = [float(el.get('x1', '0.0')), float(el.get('y1', '0.0')),
                    float(el.get('x2', '1.0')), float(el.get('y2', '1.0'))]
        self.font = el.get('font')
        el2 = el.find('text')
        if el2 != None:
            self.color = el2.get('color', '#fff')
        el2 = el.find('shadow')
        if el2 != None:
            self.shadow_color = el2.get('color', '#000')
            self.shadow_opacity = float(el2.get('opacity', 0.4))
            self.shadow_offset = [float(el2.get('offsetx', 0.1)),
                                  float(el2.get('offsety', 0.1))]


class _RenderableSection(_Renderable):
    """
    An abstract class defining objects that can be created from presentation types.
    """
    def __init__(self, align=LEFT, valign=TOP, margin=0, pos=None):
        _Renderable.__init__(self, pos)
        self.align = align
        self.valign = valign
        self.margin = margin
    
    def _set_pos(self, section):
        "Sets the position based on the section and the margin."
        try:
            self.pos = self.__old_pos[:]
        except Exception:
            self.__old_pos = self.pos[:]
        h = section.pos[3] - section.pos[1]
        w = section.pos[2] - section.pos[0]
        self.pos[0] = section.pos[0] + w * self.pos[0]
        self.pos[1] = section.pos[1] + h * self.pos[1]
        self.pos[2] = section.pos[2] - w * (1.0 - self.pos[2])
        self.pos[3] = section.pos[3] - h * (1.0 - self.pos[3])
    
    def draw(self, ccontext, bounds, section):
        "Render to a Cairo Context."
        if section:
            self._set_pos(section)
        _Renderable.draw(self, ccontext, bounds)
        self.rpos[0] += self.margin
        self.rpos[1] += self.margin
        self.rpos[2] -= self.margin
        self.rpos[3] -= self.margin
        assert self.rpos[0] < self.rpos[2]
        assert self.rpos[1] < self.rpos[3]


class Text(_RenderableSection):
    """
    A textual area that will be rendered to the screen.
    
    The text can be formatted according to the Pango Markup Language
    (http://www.pygtk.org/docs/pygtk/pango-markup-language.html).
    """
    def __init__(self, markup, align=LEFT, valign=TOP, margin=0,
                 pos=None):
        _RenderableSection.__init__(self, align, valign, margin, pos)
        self.markup = markup
    
    def draw(self, ccontext, bounds, section):
        "Render to a Cairo Context."
        _RenderableSection.draw(self, ccontext, bounds, section)
        
        layout = ccontext.create_layout()
        layout.set_width(int(self.rpos[2] - self.rpos[0])*pango.SCALE)
        if section.font:
            font_descr = pango.FontDescription(section.font)
        else:
            font_descr = pango.FontDescription("Sans 24")
        layout.set_font_description(font_descr)
        if self.align != None:
            layout.set_alignment(self.align)
        layout.set_markup(self.markup)
        
        while layout.get_pixel_size()[1] > self.rpos[3] - self.rpos[1]:
            font_descr.set_size(int(font_descr.get_size()*0.95))
            layout.set_font_description(font_descr)
        if self.valign == TOP:
            top = self.rpos[1]
        elif self.valign == MIDDLE:
            top = self.rpos[1] + (self.rpos[3] - self.rpos[1]) / 2 - \
                  layout.get_pixel_size()[1] / 2
        else:
            top = self.rpos[3] - layout.get_pixel_size()[1]
        
        if section.shadow_color:
            clr = gtk.gdk.color_parse(section.shadow_color)
            ccontext.set_source_rgba(clr.red / 65535.0, clr.green / 65535.0,
                                     clr.blue / 65535.0,
                                     section.shadow_opacity * 0.05)
            sz = font_descr.get_size() / pango.SCALE
            shadow_center = [self.rpos[0] + sz * section.shadow_offset[0],
                             top + sz * section.shadow_offset[1]]
            for x in range(-2, 3, 1):
                for y in range(-2, 3, 1):
                    ccontext.move_to(shadow_center[0]+x, shadow_center[1]+y)
                    ccontext.show_layout(layout)
        
        clr = gtk.gdk.color_parse(section.color)
        ccontext.set_source_rgba(clr.red / 65535.0, clr.green / 65535.0,
                                 clr.blue / 65535.0, 1.0)
        ccontext.move_to(self.rpos[0], top)
        ccontext.show_layout(layout)


class Image(_RenderableSection):
    """
    An image to be rendered on the screen.
    """
    def __init__(self, src, aspect=ASPECT_FIT, align=CENTER, valign=MIDDLE,
                 margin=0, pos=None):
        _RenderableSection.__init__(self, align, valign, margin, pos)
        self.src = src
        self.aspect = aspect
        self._original = None
        self._cache = {'x': None}
    
    def load(self, size):
        "Loads an image based on a requested size [width, height]."
        if not self._original:
            try:
                self._original = pb_new(self.src)
            except gobject.GError:
                exposong.log.error('Could not find "%s".', self.src)
                return False
        
        skey = 'x'.join(map(str, get_size(self._original, size, self.aspect)))
        if skey not in self._cache:
            self._cache[skey] = scale_image(self._original, size, self.aspect)
        return self._cache[skey]
    
    def draw(self, ccontext, bounds, section):
        "Render to a Cairo Context."
        _RenderableSection.draw(self, ccontext, bounds, section)
        
        size = map(_subtract, self.rpos[2:4], self.rpos[:2])
        
        img = self.load(size)
        if self.valign == TOP:
            top = self.rpos[1]
        elif self.valign == MIDDLE:
            top = self.rpos[1] + (self.rpos[3] - self.rpos[1]) / 2 - \
                  img.get_height() / 2
        else:
            top = self.rpos[3] - img.get_height()
        
        if self.align == LEFT:
            left = self.rpos[0]
        elif self.align == CENTER:
            left = self.rpos[0] + (self.rpos[2] - self.rpos[0]) / 2 - \
                  img.get_width() / 2
        else:
            left = self.rpos[2] - img.get_width()
        
        if img:
            ccontext.set_source_pixbuf(img, left, top)
            ccontext.paint()


##########################
#### Helper functions ####

def get_size(pb, size, aspect=None):
    """Gets the size according to the aspect ratio for a resized image."""
    if aspect == ASPECT_FIT:
        w, h = map(int, size)
        scaleW = float(size[0]) / pb.get_width()
        scaleH = float(size[1]) / pb.get_height()
        if scaleH < scaleW:
            scale = scaleH
        else:
            scale = scaleW
        w = int(pb.get_width() * scale)
        h = int(pb.get_height() * scale)
        return map(int, [w, h])
    else:
        return size

def scale_image(pb, size, aspect=None):
    """Scales the pixbuf (pb) to size.
    
    size:   [width, height]
    aspect: Any of the following:
             * None - scales width and height individually
             * ASPECT_FIT - size will be smaller
             * ASPECT_FILL - image will scale up
    """
    npb = None
    if aspect == ASPECT_FIT:
        w, h = map(int, size)
        scaleW = float(size[0]) / pb.get_width()
        scaleH = float(size[1]) / pb.get_height()
        if scaleH < scaleW:
            scale = scaleH
        else:
            scale = scaleW
        w = int(pb.get_width() * scale)
        h = int(pb.get_height() * scale)
        npb = gtk.gdk.Pixbuf(pb.get_colorspace(), pb.get_has_alpha(),
                             pb.get_bits_per_sample(),
                             int(w), int(h))

        pb.scale(npb, 0, 0, w, h, 0, 0, scale, scale,
                 gtk.gdk.INTERP_BILINEAR)
    elif aspect == ASPECT_FILL:
        npb = gtk.gdk.Pixbuf(pb.get_colorspace(), pb.get_has_alpha(),
                             pb.get_bits_per_sample(),
                             int(size[0]), int(size[1]))
        w, h = map(int, size)
        scaleW = float(size[0]) / pb.get_width()
        scaleH = float(size[1]) / pb.get_height()
        if scaleH > scaleW:
            scale = scaleH
        else:
            scale = scaleW
        w = int(pb.get_width() * scale)
        h = int(pb.get_height() * scale)
        
        pb.scale(npb, 0, 0, int(size[0]), int(size[1]), int(size[0] - w) / 2,
                 int(size[1] - h) / 2, scale, scale, gtk.gdk.INTERP_BILINEAR)
    else:
        npb = pb.scale_simple(int(size[0]), int(size[1]),
                              gtk.gdk.INTERP_BILINEAR)
    return npb

def _product(*args):
    "Multiply all arguments."
    return reduce(operator.mul, args)

def _subtract(*args):
    "Subtract a from b."
    return reduce(operator.sub, args[:2])

def _add(*args):
    "Add all arguments."
    return reduce(operator.add, args[:2])
