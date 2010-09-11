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
import os
import os.path
import shutil
import tempfile
import tarfile
import mimetypes

from exposong.plugins import _abstract, Plugin
from exposong import DATA_PATH, schedlist
from exposong.glob import *
import exposong.application

"""
Adds functionality to move schedules, or a full library to another exposong
instance.
"""

information = {
    'name': _("Export/Import Functions"),
    'description': __doc__,
    'required': False,
}

FILE_EXT = ".expo"
_FILTER = gtk.FileFilter()
_FILTER.set_name("ExpoSong Archive")
_FILTER.add_pattern("*.expo")

class ExportImport(Plugin, _abstract.Menu):
    '''
    Export or Import from file.
    
    A .expo file is a tar.gz file, with the following format:
        sched/ - folder contains all schedule xml files.
        pres/ - folder containing all presentation files.
        image/ - contains files for image presentations.
    '''
    def __init__(self):
        pass
    
    @classmethod
    def export_sched(cls, *args):
        'Export a single schedule with belonging presentations to file.'
        sched = schedlist.schedlist.get_active_item()
        if not sched:
            return False
        dlg = gtk.FileChooserDialog(_("Export Current Schedule"),
                                    exposong.application.main,
                                    gtk.FILE_CHOOSER_ACTION_SAVE,
                                    (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                    gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        dlg.add_filter(_FILTER)
        dlg.set_do_overwrite_confirmation(True)
        dlg.set_current_folder(os.path.expanduser("~"))
        dlg.set_current_name(os.path.basename(title_to_filename(sched.title))+".expo")
        if dlg.run() == gtk.RESPONSE_ACCEPT:
            oldpath = os.getcwd()
            os.chdir(DATA_PATH)
            fname = dlg.get_filename()
            if not fname.endswith(".expo"):
                fname += ".expo"
            tar = tarfile.open(fname, "w:gz")
            for item in cls._get_sched_list():
                tar.add(item[0], item[1])
            tar.close()
        dlg.destroy()
        
    @classmethod
    def _get_sched_list(cls, *args):
        'Returns a list with a single schedule and belonging presentations'
        exposong.application.main._save_schedules()
        sched = schedlist.schedlist.get_active_item()
        sched_list = []
        sched_list.append((os.path.join(DATA_PATH, "sched", sched.filename),
                           os.path.join("sched",
                           os.path.basename(sched.filename))))
        itr = sched.get_iter_first()
        while itr:
            fn = os.path.basename(sched.get_value(itr, 0).filename)
            sched_list.append((os.path.join(DATA_PATH, "pres", fn),
                               os.path.join("pres", fn)))
            if sched.get_value(itr, 0).get_type() == 'image':
                for slide in sched.get_value(itr, 0).slides:
                    fn = os.path.basename(slide.image)
                    sched_list.append((os.path.join(DATA_PATH, "image", fn),
                                       os.path.join("image", fn)))
            itr = sched.iter_next(itr)
        return sched_list
    
    @classmethod
    def export_lib(cls, *args):
        'Export the full library to tar-compressed file.'
        dlg = gtk.FileChooserDialog(_("Export Library"), exposong.application.main,
                                    gtk.FILE_CHOOSER_ACTION_SAVE,
                                    (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                    gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        dlg.add_filter(_FILTER)
        dlg.set_do_overwrite_confirmation(True)
        dlg.set_current_name(_("exposong_library.expo"))
        dlg.set_current_folder(os.path.expanduser("~"))
        if dlg.run() == gtk.RESPONSE_ACCEPT:
            fname = dlg.get_filename()
            if not fname.endswith(".expo"):
                fname += ".expo"
            tar = tarfile.open(fname, "w:gz")
            for item in cls._get_library_list():
                tar.add(item[0], item[1])
            tar.close()
        dlg.destroy()
        
    @classmethod
    def _get_library_list(cls, *args):
        'Returns a list with all items in pres, image and sched folder'
        #Make sure schedules are up to date.
        exposong.application.main._save_schedules() 
        library = exposong.application.main.library
        itr = library.get_iter_first()
        lib_list = []
        while itr:
            fn = library.get_value(itr, 0).filename
            lib_list.append((fn, os.path.join("pres", os.path.split(fn)[1])))
            if library.get_value(itr, 0).get_type() == 'image':
                for slide in library.get_value(itr, 0).slides:
                    lib_list.append((slide.image, os.path.join("image",
                                     os.path.split(slide.image)[1])))
            itr = library.iter_next(itr)
        model = schedlist.schedlist.get_model()
        itr = model.iter_children(schedlist.schedlist.custom_schedules)
        while itr:
            fn = model.get_value(itr, 0).filename
            lib_list.append((fn, os.path.join("sched", os.path.split(fn)[1])))
            itr = model.iter_next(itr)
        return lib_list
    
    @classmethod
    def export_backgrounds(cls, *args):
        'Export the backgrounds to tar-compressed file'
        dlg = gtk.FileChooserDialog(_("Export Backgrounds"), exposong.application.main,
                                    gtk.FILE_CHOOSER_ACTION_SAVE,
                                    (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                    gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        dlg.add_filter(_FILTER)
        dlg.set_do_overwrite_confirmation(True)
        dlg.set_current_folder(os.path.expanduser("~"))
        dlg.set_current_name(_("exposong_backgrounds.expo"))
        if dlg.run() == gtk.RESPONSE_ACCEPT:
            fname = dlg.get_filename()
            if not fname.endswith(".expo"):
                fname += ".expo"
            tar = tarfile.open(fname, "w:gz")
            for pic in cls._get_background_list():
                tar.add(pic[0], pic[1])
            tar.close()
        dlg.destroy()
    
    @classmethod
    def _get_background_list(cls, *args):
        'Returns a list with all images in bg folder'
        dir = os.path.join(DATA_PATH, "bg")
        dir_list = os.listdir(dir)
        image_list = []
        for filenm in dir_list:
            if os.path.isfile(os.path.join(dir, filenm)):
                mime = mimetypes.guess_type(filenm)
                if mime[0] and mime[0].startswith("image"):
                    image_list.append((os.path.join(dir, filenm),
                                       os.path.join("bg", filenm)))
        return image_list
    
    @classmethod
    def import_file(cls, *args):
        'Import a schedule, backgrounds or library.'
        dlg = gtk.FileChooserDialog(_("Import"), exposong.application.main,
                                    gtk.FILE_CHOOSER_ACTION_OPEN,
                                    (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                    gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        dlg.add_filter(_FILTER)
        dlg.set_current_folder(os.path.expanduser("~"))
        if dlg.run() == gtk.RESPONSE_ACCEPT:
            tar = tarfile.open(dlg.get_filename(), "r:gz")
            # Make a temporary directory so that no files are overwritten.
            tmpdir = tempfile.mkdtemp(os.path.split(
                                      dlg.get_filename())[1].rstrip(".expo"))
            tar.extractall(tmpdir)
            tar.close()
            imgs2rename = []
            if os.path.isdir(os.path.join(tmpdir, "image")):
                for nm in os.listdir(os.path.join(tmpdir,"image")):
                    if not os.path.exists(os.path.join(DATA_PATH, "image", nm)):
                        shutil.move(os.path.join(tmpdir, "image", nm),
                                    os.path.join(DATA_PATH, "image", nm))
                    else:
                        nm2 = find_freefile(os.path.join(DATA_PATH, "image", nm))
                        shutil.move(os.path.join(tmpdir, "image", nm), 
                                    os.path.join(DATA_PATH, "image", nm2))
                        imgs2rename.append((nm,nm2.rpartition(os.sep)[2]))

            if os.path.isdir(os.path.join(tmpdir, "pres")):
                pres2rename = []
                for nm in os.listdir(os.path.join(tmpdir,"pres")):
                    # Rename Images
                    if len(imgs2rename) > 0:
                        infl = open(os.path.join(tmpdir,"pres",nm),"r")
                        outfl = open(os.path.join(tmpdir,"pres",nm+".1"),"w")
                        for ln in infl:
                            for img in imgs2rename:
                                ln = re.subn(r"\b"+img[0]+r"\b",img[1],ln)[0]
                            outfl.write(ln)
                        infl.close()
                        outfl.close()
                        shutil.move(os.path.join(tmpdir,"pres",nm+".1"),
                                    os.path.join(tmpdir,"pres",nm))
                    if not os.path.exists(os.path.join(DATA_PATH, "pres", nm)):
                        shutil.move(os.path.join(tmpdir, "pres", nm),
                                    os.path.join(DATA_PATH, "pres", nm))
                        exposong.application.main.load_pres(nm)
                    else:
                        nm2 = find_freefile(os.path.join(DATA_PATH, "pres", nm))
                        nm2 = nm2.rpartition(os.sep)[2]
                        shutil.move(os.path.join(tmpdir, "pres", nm), 
                                    os.path.join(DATA_PATH, "pres", nm2))
                        exposong.application.main.load_pres(nm2)
                        pres2rename.append((nm,nm2))

            if os.path.isdir(os.path.join(tmpdir, "sched")):
                for nm in os.listdir(os.path.join(tmpdir,"sched")):
                    # Rename presentations
                    if len(pres2rename) > 0:
                        infl = open(os.path.join(tmpdir,"sched",nm),"r")
                        outfl = open(os.path.join(tmpdir,"sched",nm+".1"),"w")
                        for ln in infl:
                            for pres in pres2rename:
                                ln = re.subn(r"\b"+pres[0]+r"\b",pres[1],ln)[0]
                            outfl.write(ln)
                        infl.close()
                        outfl.close()
                        shutil.move(os.path.join(tmpdir,"sched",nm+".1"),
                                    os.path.join(tmpdir,"sched",nm))

                    if not os.path.exists(os.path.join(DATA_PATH, "sched", nm)):
                        shutil.move(os.path.join(tmpdir, "sched", nm),
                                    os.path.join(DATA_PATH, "sched", nm))
                        exposong.application.main.load_sched(nm)
                    else:
                        nm2 = find_freefile(os.path.join(DATA_PATH, "sched", nm))
                        nm2 = nm2.rpartition(os.sep)[2]
                        shutil.move(os.path.join(tmpdir, "sched", nm),
                                    os.path.join(DATA_PATH, "sched", nm2))
                        exposong.application.main.load_sched(nm2)

            if os.path.isdir(os.path.join(tmpdir, "bg")):
                images = os.listdir(os.path.join(tmpdir, "bg"))
                for i in range(len(images)):
                    images[i] = os.path.join(tmpdir, "bg", images[i])
                exposong.bgselect.bgselect.add_images(images)
        
        dlg.destroy()

    @classmethod
    def merge_menu(cls, uimanager):
        'Merge new values with the uimanager.'
        actiongroup = gtk.ActionGroup('export-import')
        actiongroup.add_actions([('import-schedule', None,
                        _("_ExpoSong Data (.expo) ..."), None,
                        _("Import a schedule, presentations or backgrounds"), cls.import_file),
                ('export-sched', None,
                 _("_Current Schedule (and belonging presentations) ..."),
                 None, None, cls.export_sched),
                ('export-lib', None, _("Whole _Library ..."), None,
                        None, cls.export_lib),
                ('export-bg', None, _("_Backgrounds ..."), None,
                        None, cls.export_backgrounds)
                ])
        uimanager.insert_action_group(actiongroup, -1)
        
        #Had to use position='top' to put them above "Quit"
        cls.menu_merge_id = uimanager.add_ui_from_string("""
            <menubar name="MenuBar">
                <menu action="File">
                    <menu action='file-import'>
                        <menuitem action="import-schedule" position="top" />
                    </menu>
                    <menu action="file-export">
                        <menuitem action="export-lib" />
                        <menuitem action="export-sched" />
                        <menuitem action="export-bg" />
                    </menu>
                </menu>
            </menubar>
            """)
    
    @classmethod
    def unmerge_menu(cls, uimanager):
        'Remove merged items from the menu.'
        uimanager.remove_ui(cls.menu_merge_id)
