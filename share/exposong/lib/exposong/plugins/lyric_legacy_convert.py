# -*- coding: utf-8 -*-
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
import gtk.gdk

import openlyrics
from xml.etree import cElementTree as etree

import exposong.application
import exposong.slidelist
from exposong.glob import *
from exposong import RESOURCE_PATH, DATA_PATH
from exposong.plugins import Plugin, _abstract
from exposong.prefs import config

"""
A converter from ExpoSong (<= 0.6.2) Lyrics type.
"""
information = {
    'name': _("ExpoSong Lyrics Converter"),
    'description': __doc__,
    'required': False,
    }

class LyricConvert(_abstract.ConvertPresentation, _abstract.Menu, Plugin):
  """
  Convert from ExpoSong (<= 0.6.2) Lyrics type to OpenLyrics.
  """
  
  @staticmethod
  def is_type(filename):
    """
    Should return True if this file should be converted.
    """
    fl = open(filename, 'r')
    match = r'<presentation\b[^>]*\btype=[\'"]lyric[\'"]'
    lncnt = 0
    for ln in fl:
      if lncnt > 2:
        break
      if re.search(match, ln):
        fl.close()
        return True
      lncnt += 1
    fl.close()
    return False
  
  @staticmethod
  def convert(filename, newfile=False):
    """
    Converts the file.
    
    filename   The name of the file for input.
    outfile    The name of the file for output. If none, `filename` will be
               overwritten.
    """
    tree = etree.parse(filename)
    if isinstance(tree, etree.ElementTree):
      root = tree.getroot()
    else:
      root = tree
    
    song = openlyrics.Song()
    title = root.findall('title')
    if title:
      song.props.titles.append(openlyrics.Title(title[0].text))
    authors = root.findall('author')
    for author in authors:
      if author.text:
        song.props.authors.append(openlyrics.Author(author.text,
                                                    author.get("type")))
    copyright = root.findall('copyright')
    if copyright:
      song.props.copyright = copyright[0].text
    order = root.findall('order')
    if order:
      song.props.order = order[0].text
    slides = root.findall('slide')
    for slide in slides:
      verse = openlyrics.Verse()
      vname = slide.get("title").lower()[0]+slide.get('title').partition(' ')[2]
      verse.name = vname
      lines = openlyrics.Lines()
      lines.lines = [openlyrics.Line(l) for l in slide.text.split('\n')]
      verse.lines = [lines]
      song.verses.append(verse)
    if newfile:
      outfile = check_filename(title_to_filename(title[0].text),
          os.path.join(DATA_PATH, "pres"))
    else:
      outfile = filename
    song.write(outfile)
    return outfile
  
  @classmethod
  def import_dialog(cls, action):
    dlg = gtk.FileChooserDialog(_("Import ExpoSong Legacy File"),
        exposong.application.main, gtk.FILE_CHOOSER_ACTION_OPEN,
        (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK,
        gtk.RESPONSE_ACCEPT))
    filter = gtk.FileFilter()
    filter.set_name("ExpoSong Legacy File")
    filter.add_pattern("*.xml")
    dlg.add_filter(filter)
    dlg.set_current_folder(os.path.expanduser("~"))
    if dlg.run() == gtk.RESPONSE_ACCEPT:
      filename = cls.convert(dlg.get_filename(), True)
      exposong.application.main.load_pres(filename)
    dlg.destroy()
  
  @classmethod
  def merge_menu(cls, uimanager):
    'Merge new values with the uimanager.'
    pass
    actiongroup = gtk.ActionGroup('lyric-legacy-grp')
    actiongroup.add_actions([('import-lyric-legacy', None,
        _('Import ExpoSong Legacy File'), None,
        _('Import a Lyric Presentation from ExpoSong before 0.7'),
        cls.import_dialog)])
    uimanager.insert_action_group(actiongroup, -1)
    
    cls.menu_merge_id = uimanager.add_ui_from_string("""
      <menubar name="MenuBar">
        <menu action="File">
          <menu action='file-import'>
            <menuitem action="import-lyric-legacy" />
          </menu>
        </menu>
      </menubar>
      """)
  
  @classmethod
  def unmerge_menu(cls, uimanager):
    'Remove merged items from the menu.'
    uimanager.remove_ui(cls.menu_merge_id)