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

import gtk
try:
    import gtkspell
except Exception:
    pass
import gobject
from xml.etree import cElementTree as etree

import exposong.application
import exposong.themeselect
import exposong._hook
import undobuffer
from exposong import RESOURCE_PATH, DATA_PATH
from exposong import theme
from exposong.glob import *
from exposong.plugins import Plugin, _abstract

"""
Plain text presentations.
"""
information = {
        'name': _("Text Presentation"),
        'description': __doc__,
        'required': False,
}
type_icon = gtk.gdk.pixbuf_new_from_file_at_size(
        os.path.join(RESOURCE_PATH,'pres_text.png'), 20, 14)

class Presentation (Plugin, _abstract.Presentation, exposong._hook.Menu,
                    _abstract.Schedule):
    """
    Text presentation type.
    """
    
    class Slide (Plugin, _abstract.Presentation.Slide):
        """
        A text slide.
        """
        def __init__(self, pres, value):
            self.pres = pres
            self._content = []
            self.title = ''
            self._theme = None
            if etree.iselement(value):
                self.title = value.get("title")
                self._theme = value.get("theme")
                for el in value:
                    k = {
                         'align': theme.CENTER,
                         'valign': theme.MIDDLE,
                         }
                    k['pos'] = [0.0, 0.0, 1.0, 1.0]
                    for name, val in el.items():
                        if name is 'x1':
                            k['pos'][0] = val
                        elif name is 'y1':
                            k['pos'][1] = val
                        elif name is 'x2':
                            k['pos'][2] = val
                        elif name is 'y2':
                            k['pos'][3] = val
                        elif name is 'align':
                            if val is 'left':
                                k['align'] = theme.LEFT
                            elif val is 'center':
                                k['align'] = theme.CENTER
                            elif val is 'right':
                                k['align'] = theme.RIGHT
                        elif name is 'valign':
                            if val is 'top':
                                k['valign'] = theme.TOP
                            elif val is 'middle':
                                k['valign'] = theme.MIDDLE
                            elif val is 'bottom':
                                k['valign'] = theme.BOTTOM
                        elif name is 'margin':
                            k['margin'] = int(val)
                    
                    if el.tag == 'text':
                        k['markup'] = element_contents(el)
                        self._content.append(theme.Text(**k))
                    elif el.tag == 'image':
                        k['src'] = os.path.join(DATA_PATH, 'image', el.get('src'))
                        if el.get('aspect') is 'fit':
                            k['aspect'] = theme.ASPECT_FIT
                        elif el.get('aspect') is 'fill':
                            k['aspect'] = theme.ASPECT_FILL
                        self._content.append(theme.Image(**k))
            
            self._set_id(value)
            _abstract.Presentation.Slide.__init__(self, pres, value)
        
        def get_theme(self):
            'Return the theme for this slide.'
            if self._theme:
                for thm in exposong.themeselect.themeselect.get_model():
                    if self._theme == os.path.split(thm[0])[1]:
                        return thm[1]
                else:
                    exposong.log.warning('Custom theme "%s" not found.' % 
                                         self._theme)
            return None
        
        def _edit_window(self, parent):
            ret = 0
            editor = SlideEdit(parent, self)
            while True:
                ans = editor.run()
                if ans == gtk.RESPONSE_ACCEPT:
                    if editor.changed:
                        self.title = editor.get_slide_title()
                        self.text = editor.get_slide_text()
                        ret = 1
                elif ans == gtk.RESPONSE_APPLY: #Close and new
                    if editor.changed:
                        self.title = editor.get_slide_title()
                        self.text = editor.get_slide_text()
                    ret = 2
                return ret
        
        def get_body(self):
            return self._content
        
        @staticmethod
        def get_version():
            "Return the version number of the plugin."
            return (1,0)
    
        @staticmethod
        def get_description():
            "Return the description of the plugin."
            return "A lyric presentation type."
    
    def __init__(self, filename=''):
        self.filename = filename
        self._meta = {}
        self.slides = []
        self._timer = None
        self._timer_loop = False
        
        if filename:
            fl = open(filename, 'r')
            if not self.is_type(fl):
                fl.close()
                raise _abstract.WrongPresentationType
            fl.close()
            
            dom = None
            try:
                dom = etree.parse(filename)
                root = dom.getroot()
            except IOError, details:
                exposong.log.error('Could not open presentation "%s": %s',
                                   filename, details)
            #except ExpatError, details:
            #    exposong.log.error('Error reading presentation file "%s": %s',
            #                       filename, details)
            else:
                for el in root.find("meta"):
                    if el.tag == 'title':
                        self._title = el.text
                    elif el.tag == 'timer':
                        self._timer = int(el.get("time"))
                        self._timer_loop = bool(el.get("loop", False))
                    else:
                        self._meta[el.tag] = el.text
                slides = root.findall("slides/slide")
                for sl in slides:
                    self.slides.append(self.Slide(self, sl))
        
        self._order = []

        # TODO Separate to new function _process_dom or likewise.
        dom = None
        if etree.iselement(dom):
            ordernode = dom.findall("order")
            if len(ordernode) > 0:
                self._order = get_node_text(ordernode[0]).split()
                for o in self._order:
                    if o.strip() == "":
                        self._order.remove(o)
    
    def _edit_tabs(self, notebook, parent):
        "Tabs for the dialog."
        vbox = gtk.VBox()
        vbox.set_border_width(4)
        vbox.set_spacing(7)
        hbox = gtk.HBox()
        
        label = gtk.Label(_("Title:"))
        label.set_alignment(0.5, 0.5)
        hbox.pack_start(label, False, True, 5)
        
        self._fields['title'] = gtk.Entry(45)
        self._fields['title'].set_text(self.get_title())
        hbox.pack_start(self._fields['title'], True, True)
        vbox.pack_start(hbox, False, True)
        
        self._fields['slides'] = gtk.ListStore(gobject.TYPE_PYOBJECT, str)
        # Add the slides
        for sl in self.get_slide_list(True):
            self._fields['slides'].append(sl)
        self._fields['slides'].connect("row-changed", self._on_slide_added)
        
        self._slide_list = gtk.TreeView(self._fields['slides'])
        self._slide_list.set_enable_search(False)
        self._slide_list.set_reorderable(True)
        # Double click to edit
        self._slide_list.connect("row-activated", self._slide_dlg, True)
        col = gtk.TreeViewColumn( _("Slide") )
        col.set_resizable(False)
        self.slide_column(col, self._fields['slides'])
        self._slide_list.append_column(col)
        
        toolbar = gtk.Toolbar()
        btn = gtk.ToolButton(gtk.STOCK_ADD)
        btn.connect("clicked", self._slide_dlg_btn, self._slide_list)
        toolbar.insert(btn, -1)
        btn = gtk.ToolButton(gtk.STOCK_EDIT)
        btn.connect("clicked", self._slide_dlg_btn, self._slide_list, True)
        toolbar.insert(btn, -1)
        btn = gtk.ToolButton(gtk.STOCK_DELETE)
        btn.connect("clicked", self._on_slide_delete, self._slide_list, parent)
        toolbar.insert(btn, -1)
        toolbar.insert(gtk.SeparatorToolItem(), -1)
        
        vbox.pack_start(toolbar, False, True)
        
        scroll = gtk.ScrolledWindow()
        scroll.add(self._slide_list)
        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scroll.set_size_request(400, 250)
        scroll.set_shadow_type(gtk.SHADOW_IN)
        vbox.pack_start(scroll, True, True)
        
        vbox.show_all()
        notebook.insert_page(vbox, gtk.Label(_("Edit")), 0)
        
        self._fields['title'].grab_focus()
        
        # TODO Ordering Lists
        #vbox = gtk.VBox()
        #notebook.insert_page(vbox, gtk.Label(_("Order")), 1)
        
        
        timer = gtk.VBox()
        timer.set_border_width(8)
        timer.set_spacing(7)
        
        # Might be used later if more things get on this tab
        #label = gtk.Label()
        #label.set_markup(_("<b>Timer</b>"))
        #label.set_alignment(0.0, 0.5)
        #timer.pack_start(label, False)
        
        self._fields['timer_on'] = gtk.CheckButton(_("Use Timer"))
        self._fields['timer_on'].set_active(self._timer is not None)
        self._fields['timer_on'].connect("toggled",
                lambda chk: self._fields['timer'].set_sensitive(chk.get_active()))
        self._fields['timer_on'].connect("toggled",
                lambda chk: self._fields['timer_loop'].set_sensitive(chk.get_active()))
        self._fields['timer_on'].connect("toggled",
                lambda chk: self._fields['timer_seconds'].set_sensitive(chk.get_active()))
        timer.pack_start(self._fields['timer_on'], False)
        
        self._fields['timer_seconds'] = gtk.Label(_("Seconds Per Slide"))
        self._fields['timer_seconds'].set_sensitive(self._timer is not None)
        hbox = gtk.HBox()
        hbox.set_spacing(18)
        hbox.pack_start(self._fields['timer_seconds'], False, False)
        
        adjust = gtk.Adjustment(1, 1, 25, 1, 3, 0)
        self._fields['timer'] = gtk.SpinButton(adjust, 1, 0)
        self._fields['timer'].set_sensitive(self._timer is not None)
        if isinstance(self._timer, (int, float)):
            self._fields['timer'].set_value(self._timer)
        hbox.pack_start(self._fields['timer'], False, False)
        timer.pack_start(hbox, False)
        
        self._fields['timer_loop'] = gtk.CheckButton(_("Loop Slides"))
        self._fields['timer_loop'].set_active(self._timer_loop)
        self._fields['timer_loop'].set_sensitive(self._timer is not None)
        timer.pack_start(self._fields['timer_loop'], False, False)
        
        notebook.append_page(timer, gtk.Label( _("Timer") ))
        
        _abstract.Presentation._edit_tabs(self, notebook, parent)
    
    def _edit_save(self):
        "Save the fields if the user clicks ok."
        self._title = self._fields['title'].get_text()
        itr = self._fields['slides'].get_iter_first()
        self.slides = []
        while itr:
            self.slides.append(self._fields['slides'].get_value(itr,0))
            itr = self._fields['slides'].iter_next(itr)
        
        # Timer
        if self._fields['timer_on'].get_active():
            self._timer = self._fields['timer'].get_value_as_int()
            self._timer_loop = self._fields['timer_loop'].get_active()
        else:
            self._timer = None
        
        _abstract.Presentation._edit_save(self)
    
    def _is_editing_complete(self, parent):
        "Test to see if all fields have been filled which are required."
        if self._fields['title'].get_text() == "":
            info_dialog = gtk.MessageDialog(parent,
                                            gtk.DIALOG_DESTROY_WITH_PARENT,
                                            gtk.MESSAGE_INFO, gtk.BUTTONS_OK,
                                            _("Please enter a Title."))
            info_dialog.run()
            info_dialog.destroy()
            return False
        if len(self._fields['slides']) == 0:
            msg = _('The presentation must have at least one slide.')
            info_dialog = gtk.MessageDialog(parent,
                                            gtk.DIALOG_DESTROY_WITH_PARENT,
                                            gtk.MESSAGE_INFO, gtk.BUTTONS_OK,
                                            msg)
            info_dialog.run()
            info_dialog.destroy()
            return False
        return _abstract.Presentation._is_editing_complete(self, parent)
    
    def _slide_dlg_btn(self, btn, treeview, edit=False):
        "Add or edit a title."
        path = None
        col = None
        if edit:
            (model, itr) = treeview.get_selection().get_selected()
            path = model.get_path(itr)
        self._slide_dlg(treeview, path, col, edit)
    
    def _slide_dlg(self, treeview, path, col, edit=False):
        "Create a dialog for a new slide."
        model = treeview.get_model()
        if edit:
            itr = model.get_iter(path)
            if not itr:
                return False
            # Edit on a copy, so Cancel will work.
            sl = model.get_value(itr, 0).copy()
            old_title = sl.title
        else:
            sl = self.Slide(self, None)
        
        ans = sl._edit_window(treeview.get_toplevel())
        if ans:
            if edit:
                if len(old_title) == 0 or old_title <> sl.title:
                    sl._set_id()
                model.set(itr, 0, sl, 1, sl.get_markup(True))
            else:
                sl._set_id()
                model.append( (sl, sl.get_markup(True)) )
        if ans == 2:
            self._slide_dlg(treeview, None, None)
    
    def _on_slide_added(self, model, path, iter):
        self._slide_list.set_cursor(path)
        
    def _on_slide_delete(self, btn, treeview, parent):
        'Remove the selected slide.'
        (model, itr) = treeview.get_selection().get_selected()
        if not itr:
            return False
        msg = _('Are you sure you want to delete this slide? This cannot be undone.')
        dialog = gtk.MessageDialog(exposong.application.main, gtk.DIALOG_MODAL,
                                   gtk.MESSAGE_WARNING, gtk.BUTTONS_YES_NO,
                                   msg)
        dialog.set_title( _('Delete Slide?') )
        resp = dialog.run()
        dialog.hide()
        if resp == gtk.RESPONSE_YES:
            model.remove(itr)

    def to_xml(self):
        'Save the data to disk.'
        if self.filename:
            self.filename = check_filename(self.get_title(), self.filename)
        else:
            self.filename = check_filename(self.get_title(),
                                           os.path.join(DATA_PATH, "pres"))
        
        root = etree.Element("presentation")
        root.attrib["type"] = self.get_type()
        root.text = "\n"
        
        node = etree.Element("title")
        node.text = self.get_title()
        node.tail = "\n"
        root.append(node)
        
        if self._timer:
            node = etree.Element("timer")
            node.attrib['time'] = str(self._timer)
            if self._timer_loop:
                node.attrib['loop'] = "1"
            node.tail = "\n"
            root.append(node)
        
        for s in self.slides:
            node = etree.Element("slide")
            s.to_node(node)
            node.tail = '\n'
            root.append(node)
        doc = etree.ElementTree(root)
        outfile = open(self.filename, 'w')
        doc.write(outfile, encoding=u'UTF-8')
    
    def get_order(self):
        "Returns the order in which the slides should be presented."
        if len(self._order) > 0:
            return tuple(self.get_slide_from_order(n) for n in self._order)
        else:
            return _abstract.Presentation.get_order(self)

    def get_slide_from_order(self, order_value):
        "Gets the slide index."
        i = 0
        for sl in self.slides:
            if(sl.id == order_value):
                return i
            i += 1
        return -1
    
    ## Timer
    
    def get_timer(self):
        'Return the time until we skip to the next slide.'
        return self._timer
    
    def is_timer_looped(self):
        'If this is True, go to the beginning when the timer reaches the end.'
        return self._timer_loop
    
    ## Slidelist view
    
    def slide_column(self, col):
        'Sets the column for slidelist.'
        col.clear()
        cr = exposong.themeselect.CellRendererTheme()
        cr.height = 100
        cr.can_cache = False
        for thm in exposong.themeselect.themeselect.get_model():
                if '_builtin_black' == thm[0]:
                    cr.theme = thm[1]
        col.pack_start(cr, False)
        col.add_attribute(cr, 'slide', 0)
    
    def get_row(self):
        'Gets the data to add to the presentation list.'
        return (self, self.get_title())
    
    ## Printing
    
    def get_print_markup(self):
        "Return the presentation markup for printing."
        markup = "<span face='sans' weight='bold' size='large'>%s</span>"\
                 % self.get_title()
        markup += "\n\n\n"
        for slide in self.get_slide_list():
            markup += "<span weight='bold' face='sans' size='%%(fontsize)d'>%s</span>\n"\
                      % slide[0].get_title()
            markup += "<span face='sans' size='%%(fontsize)d'>%s</span>\n\n" % slide[0].get_text()
        
        return markup
    
    def can_print(self):
        "Return True of printing is available."
        return True
    
    @classmethod
    def is_type(cls, fl):
        match = r'<presentation\b'
        lncnt = 0
        for ln in fl:
                if lncnt > 2:
                    break
                if re.search(match, ln):
                        return True
                lncnt += 1
        return False
    
    @staticmethod
    def get_type():
        "Return the presentation type."
        return 'text'
    
    @staticmethod
    def get_icon():
        "Return the pixbuf icon."
        return type_icon
    
    @classmethod
    def merge_menu(cls, uimanager):
        "Merge new values with the uimanager."
        factory = gtk.IconFactory()
        factory.add('exposong-text',gtk.IconSet(gtk.gdk.pixbuf_new_from_file(
                os.path.join(RESOURCE_PATH,'pres_text.png'))))
        factory.add_default()
        gtk.stock_add([('exposong-text',_('_Text'), gtk.gdk.MOD1_MASK, 
                0, 'pymserv')])
        
        actiongroup = gtk.ActionGroup('exposong-text')
        actiongroup.add_actions([('pres-new-text', 'exposong-text', None, None,
                None, cls._on_pres_new)])
        uimanager.insert_action_group(actiongroup, -1)
        
        cls.menu_merge_id = uimanager.add_ui_from_string("""
            <menubar name='MenuBar'>
                <menu action='Presentation'>
                        <menu action='pres-new'>
                            <menuitem action='pres-new-text' />
                        </menu>
                </menu>
            </menubar>
            """)
    
    @classmethod
    def unmerge_menu(cls, uimanager):
        "Remove merged items from the menu."
        uimanager.remove_ui(cls.menu_merge_id)
    
    @classmethod
    def schedule_name(cls):
        "Return the string schedule name."
        return _('Text Presentations')
    
    @classmethod
    def schedule_filter(cls, pres):
        "Called on each presentation, and return True if it can be added."
        return pres.__class__ is cls
    
    @staticmethod
    def get_version():
        "Return the version number of the plugin."
        return (1,0)
    
    @staticmethod
    def get_description():
        "Return the description of the plugin."
        return 'A text presentation type.'


class SlideEdit(gtk.Dialog):
    """Create a new window for editing a single slide.
         Contains a title field, a toolbar and a TextView.
    """
    def __init__(self, parent, slide):
        gtk.Dialog.__init__(self, _("Editing Slide"), parent,
                            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
        
        self._build_menu()
        
        newbutton = self.add_button(_("Save and New"), gtk.RESPONSE_APPLY)
        newimg = gtk.Image()
        newimg.set_from_stock(gtk.STOCK_NEW, gtk.ICON_SIZE_BUTTON)
        newbutton.set_image(newimg)
        newbutton.connect("clicked", self._quit_with_save)
        cancelbutton = self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT)
        cancelbutton.connect("clicked", self._quit_without_save)
        okbutton = self.add_button(gtk.STOCK_OK, gtk.RESPONSE_ACCEPT)
        okbutton.connect("clicked", self._quit_with_save)
        
        self.connect("delete-event", self._quit_without_save)
        
        self.slide_title = slide.title
        self.slide_text = slide.text
        self.changed = False
        
        self.set_border_width(4)
        self.vbox.set_spacing(7)
        
        # Title
        self.vbox.pack_start(self._get_title_box(), False, True)
        
        # Toolbar
        self._toolbar = gtk.Toolbar()
        self.undo_btn = self._get_toolbar_item(gtk.ToolButton(gtk.STOCK_UNDO),
                                               self._undo, False)
        self.redo_btn = self._get_toolbar_item(gtk.ToolButton(gtk.STOCK_REDO),
                                               self._redo, False)
        self.vbox.pack_start(self._toolbar, False, True)
        
        self._buffer = self._get_buffer()
        self._buffer.connect("changed", self._on_text_changed)
        
        text = gtk.TextView()
        text.set_wrap_mode(gtk.WRAP_NONE)
        text.set_buffer(self._buffer)
        try:
            gtkspell.Spell(text)
        except Exception:
            pass
        scroll = gtk.ScrolledWindow()
        scroll.add(text)
        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scroll.set_size_request(400, 250)
        scroll.set_shadow_type(gtk.SHADOW_IN)
        self.vbox.pack_start(scroll, True, True)
        
        self.vbox.show_all()
        
    def _build_menu(self):
        self.uimanager = gtk.UIManager()
        self.add_accel_group(self.uimanager.get_accel_group())
        self._actions = gtk.ActionGroup('main')
        self._actions.add_actions([
                ('Edit', None, '_Edit' ),
                ("edit-undo", gtk.STOCK_UNDO, "Undo",
                    "<Ctrl>z", "Undo the last operation", self._undo),
                ("edit-redo", gtk.STOCK_REDO, "Redo",
                    "<Ctrl>y", "Redo the last operation", self._redo)
                ])
        self.uimanager.insert_action_group(self._actions, 0)
        self.uimanager.add_ui_from_string('''
                <menubar name='MenuBar'>
                    <menu action='Edit'>
                        <menuitem action='edit-undo'/>
                        <menuitem action='edit-redo'/>
                    </menu>
                </menubar>''')
    
    def _get_title_box(self):
        hbox = gtk.HBox()
        self._title_label = gtk.Label(_('Title:'))
        self._title_label.set_alignment(0.5,0.5)
        hbox.pack_start(self._title_label, False, True)
        
        self._title_entry = gtk.Entry()
        self._title_entry.set_text(self.slide_title)
        hbox.pack_start(self._title_entry, True, True)
        return hbox
        
    def _get_toolbar_item(self, toolbutton, proxy, sensitive=True):
        btn = toolbutton
        btn.set_sensitive(sensitive)
        btn.connect('clicked', proxy)
        self._toolbar.insert(btn, -1)
        return btn
    
    def _get_buffer(self):
        buffer = undobuffer.UndoableBuffer()
        buffer.begin_not_undoable_action()
        buffer.set_text(self.slide_text)
        buffer.end_not_undoable_action()
        buffer.set_modified(False)
        return buffer
    
    def get_slide_title(self):
        "Returns the title of the edited slide."
        return self.slide_title
    
    def get_slide_text(self):
        "Returns the text of the edited slide."
        return self.slide_text
    
    def _save(self):
        self.slide_title = self._get_title_value()
        bounds = self._buffer.get_bounds()
        self.slide_text = self._buffer.get_text(bounds[0], bounds[1])
        self.changed = True
    
    def _ok_to_continue(self):
        if self._buffer.can_undo or self._get_title_value() != self.slide_title:
            msg = _('Unsaved Changes exist. Do you really want to continue without saving?')
            dlg = gtk.MessageDialog(self, gtk.DIALOG_MODAL,
                    gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, msg)
            resp = dlg.run()
            dlg.destroy()
            if resp == gtk.RESPONSE_NO:
                return False
        self.changed = False
        return True
    
    def _on_text_changed(self, event):
        self.undo_btn.set_sensitive(self._buffer.can_undo)
        self.redo_btn.set_sensitive(self._buffer.can_redo)
        if self._buffer.can_undo:
            if not self.get_title().startswith("*"):
                self.set_title("*%s"%self.get_title())
        else:
            self.set_title(self.get_title().lstrip("*"))
    
    def _undo(self, event):
        self._buffer.undo()
    
    def _redo(self, event):
        self._buffer.redo()
        
    def _get_title_value(self):
        return self._title_entry.get_text()
    
    def _quit_with_save(self, event, *args):
        if self._get_title_value() == "":
            info_dialog = gtk.MessageDialog(self,
                    gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO,
                    gtk.BUTTONS_OK, _("Please enter a Title."))
            info_dialog.run()
            info_dialog.destroy()
            self._title_entry.grab_focus()
            return False
        self._save()
        self.destroy()
    
    def _quit_without_save(self, event, *args):
        if self._ok_to_continue():
            self.destroy()

