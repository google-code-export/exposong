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
The SlideList class displays the slides for the currently select presentation.
"""

import gtk
import gobject
import pango
import random

import exposong.screen
from exposong import config

slidelist = None #will hold instance of SlideList
slide_scroll = None

class SlideList(gtk.TreeView, exposong._hook.Menu):
    '''
    The slides of a presentation.
    '''
    def __init__(self):
        "Create the interface."
        self.pres = None
        self.slide_order = ()
        self.slide_order_index = -1
        # Used to stop or reset the timer if the presentation or slide changes.
        self.__timer = 0

        gtk.TreeView.__init__(self)
        self.set_size_request(250, -1)
        self.set_enable_search(False)
        #self.set_headers_visible(False)
        
        self.column1 = gtk.TreeViewColumn( _("Slides"))
        self.column1.set_resizable(False)
        self.append_column(self.column1)
        
        self.set_model(gtk.ListStore(gobject.TYPE_PYOBJECT, gobject.TYPE_STRING))
        self.get_selection().connect("changed", self._on_slide_activate)
    
    def set_presentation(self, pres):
        'Set the active presentation.'
        self.pres = pres
        slist = self.get_model()
        slist.clear()
        
        if pres is None:
            return
        
        self.set_model(slist)
        exposong.log.debug('Activating "%s" %s presentation.',
                           pres.get_title(), pres.get_type())
        if not hasattr(self, 'pres_type') or self.pres_type is not pres.get_type():
            self.pres_type = pres.get_type()
            pres.slide_column(self.column1)
        
        if config.config.get('songs', 'show_in_order') == "True" and pres.get_type() == "song":
            slides = pres.get_slides_in_order()
        else:
            slides = pres.get_slide_list()
        for slide in slides:
            slist.append(slide)
        
        if pres.get_type() == "song":
            custom_order = not config.config.get('songs', 'show_in_order') == "True"
            self.slide_order = pres.get_order(custom_order)
        else:
            self.slide_order = pres.get_order()
        self.slide_order_index = -1
        
        self.__timer += 1
        men = slist.get_iter_first() is not None
        self._actions.get_action("pres-slide-next").set_sensitive(men)
        self._actions.get_action("pres-slide-prev").set_sensitive(men)
    
    def get_active_item(self):
        'Return the selected `Slide` object.'
        (model, s_iter) = self.get_selection().get_selected()
        if s_iter:
            return model.get_value(s_iter, 0)
        else:
            return False
    
    def _move_to_slide(self, mv):
        'Move to the slide at mv. This ignores slide_order_index.'
        order_index = self.slide_order_index
        if self.slide_order_index == -1 and\
                self.get_selection().count_selected_rows() > 0:
            (model,itr) = self.get_selection().get_selected()
            cur = model.get_string_from_iter(itr)
            cnt = 0
            for o in self.slide_order:
                if o == int(cur):
                    if len(self.slide_order) > cnt+mv and cnt+mv > 0:
                        self.to_slide(self.slide_order[cnt+mv])
                        self.slide_order_index = cnt+mv
                        return True
                    else:
                        return False
                cnt += 1
        if order_index == self.slide_order_index and \
                len(self.slide_order) > order_index+mv and order_index+mv >= 0:
            self.to_slide(self.slide_order[order_index + mv])
            self.slide_order_index = order_index + mv
            return True
        return False
    
    def prev_slide(self, *args):
        'Move to the previous slide.'
        return self._move_to_slide(-1)
    
    def next_slide(self, *args):
        'Move to the next slide.'
        return self._move_to_slide(1)
    
    def to_start(self):
        'Reset to the first slide.'
        self.slide_order_index = 0
        if len(self.slide_order):
            self.to_slide(self.slide_order[0])
            return True
        return False
    
    def to_slide(self, slide_num):
        model = self.get_model()
        itr = model.iter_nth_child(None, slide_num)
        if itr:
            selection = self.get_selection()
            selection.select_iter(itr)
            self.scroll_to_cell(model.get_path(itr))
    
    def _on_slide_activate(self, *args):
        'Present the selected slide to the screen.'
        exposong.screen.screen.draw()
        self.slide_order_index = -1
        
        self.reset_timer()
    
    def reset_timer(self):
        'Restart the timer.'
        self.__timer += 1
        if self.pres and self.pres.get_timer():
            gobject.timeout_add(self.pres.get_timer()*1000, self._set_timer,
                                self.__timer)
    
    def _set_timer(self, t):
        'Starts the timer, or continues a current timer.'
        if t <> self.__timer:
            return False
        if not exposong.screen.screen.is_running():
            return False
        if not self.next_slide(None) and self.pres.is_timer_looped():
            self.to_start()
        # Return False, because the slide is activated, adding another timeout
        return False
    
    def toggle_show_order(self, widget):
        'Called when the "pres-show-in-order" action was toggled'
        config.config.set("songs", "show_in_order", str(widget.get_active()))
        self.set_presentation(self.pres)
    
    @classmethod
    def merge_menu(cls, uimanager):
        'Merge new values with the uimanager.'
        global slidelist
        cls._actions = gtk.ActionGroup('slidelist')
        cls._actions.add_actions([
                ('pres-slide-prev', None, _("Previous Slide"), "Page_Up", None,
                        slidelist.prev_slide),
                ('pres-slide-next', None, _("Next Slide"), "Page_Down", None,
                        slidelist.next_slide),
                ])
        cls._actions.add_toggle_actions([
            ('pres-show-in-order', None, _("Show Slides in Order"), None, None,
                        slidelist.toggle_show_order),
        ])
        
        uimanager.insert_action_group(cls._actions, -1)
        uimanager.add_ui_from_string("""
            <menubar name="MenuBar">
                <menu action="Presentation">
                    <menuitem action="pres-slide-prev" position="bot" />
                    <menuitem action="pres-slide-next" position="bot" />
                    <menuitem action="pres-show-in-order" position="bot" />
                </menu>
            </menubar>
            """)
        cls._actions.get_action("pres-slide-next").set_sensitive(False)
        cls._actions.get_action("pres-slide-prev").set_sensitive(False)
        action = cls._actions.get_action('pres-show-in-order')
        if config.config.get('songs', 'show_in_order') == "True":
            action.set_active(True)
        exposong.preslist.preslist.get_selection().connect('changed',
                                cls._show_in_order_active, action)
        # unmerge_menu not implemented, because we will never uninstall this as
        # a module.
    
    @classmethod
    def get_order_checkbutton(cls):
        "Return the 'Use Order' checkbox"
        cb = gtk.CheckButton()
        cls._actions.get_action('pres-show-in-order').connect_proxy(cb)
        return cb
    
    @staticmethod
    def _show_in_order_active(sel, action):
        if sel.count_selected_rows() > 0:
            (model, itr) = sel.get_selected()
            pres = model.get_value(itr, 0)
            if pres and pres.get_type() == 'song':
                action.set_sensitive(True)
                return
        action.set_sensitive(False)
