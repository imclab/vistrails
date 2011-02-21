###########################################################################
##
## Copyright (C) 2006-2010 University of Utah. All rights reserved.
##
## This file is part of VisTrails.
##
## This file may be used under the terms of the GNU General Public
## License version 2.0 as published by the Free Software Foundation
## and appearing in the file LICENSE.GPL included in the packaging of
## this file.  Please review the following to ensure GNU General Public
## Licensing requirements will be met:
## http://www.opensource.org/licenses/gpl-license.php
##
## If you are unsure which license is appropriate for your use (for
## instance, you are interested in developing a commercial derivative
## of VisTrails), please contact us at vistrails@sci.utah.edu.
##
## This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
## WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
##
############################################################################

from PyQt4 import QtCore, QtGui

import glob
import os
from datetime import datetime
from time import strptime
from core import debug
from core.thumbnails import ThumbnailCache
from core.collection import Collection
from core.collection.search import SearchCompiler, SearchParseError
from core.db.locator import FileLocator
from gui.common_widgets import QToolWindowInterface, QToolWindow, QSearchBox
from gui.theme import CurrentTheme

class QCollectionWidget(QtGui.QTreeWidget):
    """ This is an abstract class that contains functions for handling
    a core.collection.Collection object
    a subclass should provide a view of the collection
    """
    def __init__(self, collection, parent=None):
        QtGui.QTreeWidget.__init__(self, parent)
        self.collection = collection
        self.collection.add_listener(self)
        self.setExpandsOnDoubleClick(False)
        self.connect(self,
                     QtCore.SIGNAL('itemDoubleClicked(QTreeWidgetItem *, int)'),
                     self.item_selected)
        self.setIconSize(QtCore.QSize(16,16))

    def setup_widget(self, workspace=None):
        """ Adds the items from the current workspace """
        pass

    def updated(self):
        """ Called from the collection when committed """
        self.setup_widget()
            
    def run_search(self, search, items=None):
        # FIXME only uses top level items
        if items is None:
            items = [self.topLevelItem(i) 
                     for i in xrange(self.topLevelItemCount())]
        for item in items:
            if search.match(item.entity):
                item.setHidden(False)
                parent = item.parent()
                while parent is not None:
                    if parent.isHidden():
                        parent.setHidden(False)
                    parent = parent.parent()
            else:
                item.setHidden(True)
            self.run_search(search, [item.child(i) 
                                     for i in xrange(item.childCount())])
            
    def reset_search(self, items=None):
        if items is None:
            items = [self.topLevelItem(i) 
                     for i in xrange(self.topLevelItemCount())]
        for item in items:
            item.setHidden(False)
            self.reset_search([item.child(i) 
                               for i in xrange(item.childCount())])

    def item_selected(self, widget_item, column):
        print 'item_selected'
        locator = widget_item.entity.locator()
        print '*** opening'
        print locator.to_url()
        print locator.name
        print '***'
        
#         fname = str(widget_item.data(2, QtCore.Qt.DisplayRole).toString())
#         tag = str(widget_item.data(1, QtCore.Qt.DisplayRole).toString())
#         print "parent emiting", fname, tag
        import gui.application
        app = gui.application.VistrailsApplication
        open_vistrail = app.builderWindow.open_vistrail_without_prompt

        workflow_exec = locator.kwargs.get('workflow_exec', None)
        args = {}
        if workflow_exec:
            args['workflow_exec'] = int(workflow_exec)
            locator = widget_item.parent().entity.locator()
        args['version'] = locator.kwargs.get('version_node', None) or \
                          locator.kwargs.get('version_tag', None)
        open_vistrail(locator, **args)
                                                       
    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        menu = QtGui.QMenu(self)
        if item:
            # find top level
            p = item
            while p.parent():
                p = p.parent()
            act = QtGui.QAction("&Update", self)
            act.setStatusTip("Update this object")
            QtCore.QObject.connect(act,
                                   QtCore.SIGNAL("triggered()"),
                                   p.refresh_object)
            menu.addAction(act)
            act = QtGui.QAction("&Remove", self)
            act.setStatusTip("Remove from this list")
            QtCore.QObject.connect(act,
                                   QtCore.SIGNAL("triggered()"),
                                   p.remove_object)
            menu.addAction(act)
            act = QtGui.QAction("", self)
            act.setSeparator(True)
            menu.addAction(act)
        act = QtGui.QAction("Check &All", self)
        act.setStatusTip("Removes deleted files")
        QtCore.QObject.connect(act,
                               QtCore.SIGNAL("triggered()"),
                               self.check_objects)
        menu.addAction(act)
        act = QtGui.QAction("Remove All", self)
        act.setStatusTip("Removes all files")
        QtCore.QObject.connect(act,
                               QtCore.SIGNAL("triggered()"),
                               self.remove_all)
        menu.addAction(act)
        act = QtGui.QAction("Add &File", self)
        act.setStatusTip("Add specified vistrail file")
        QtCore.QObject.connect(act,
                               QtCore.SIGNAL("triggered()"),
                               self.add_file)
        menu.addAction(act)
        act = QtGui.QAction("Add from &Directory", self)
        act.setStatusTip("Add all vistrail files in a directory")
        QtCore.QObject.connect(act,
                               QtCore.SIGNAL("triggered()"),
                               self.add_dir)
        menu.addAction(act)
        act = QtGui.QAction("", self)
        act.setSeparator(True)
        menu.addAction(act)
        act = QtGui.QAction("Add a new Workspace", self)
        act.setStatusTip("Create a new workspace")
        QtCore.QObject.connect(act,
                               QtCore.SIGNAL("triggered()"),
                               self.add_workspace)
        menu.addAction(act)
        if self.collection.currentWorkspace != 'Default':
            act = QtGui.QAction("Delete Workspace", self)
            act.setStatusTip("Remove current workspace")
            QtCore.QObject.connect(act,
                                   QtCore.SIGNAL("triggered()"),
                                   self.delete_workspace)
            menu.addAction(act)
        menu.exec_(event.globalPos())

    def check_objects(self):
        items = [self.topLevelItem(i) 
                 for i in xrange(self.topLevelItemCount())]
        for item in items:
            if not self.collection.urlExists(item.entity.url):
                self.collection.delete_entity(item.entity) 
        self.collection.commit()

    def remove_all(self):
        items = [self.topLevelItem(i) 
                 for i in xrange(self.topLevelItemCount())]
        for item in items:
            self.collection.del_from_workspace(item.entity) 
        self.collection.commit()

    def add_file(self):
        s = QtGui.QFileDialog.getOpenFileName(
                    self, "Choose a file",
                    "", "Vistrail files (*.vt *.xml)");
        if str(s):
            locator = FileLocator(str(s))
            url = locator.to_url()
            entity = self.collection.updateVistrail(url)
            # add to relevant workspace categories
            self.collection.add_to_workspace(entity)
            self.collection.commit()
        
    def add_dir(self):
        s = QtGui.QFileDialog.getExistingDirectory(
                    self, "Choose a directory",
                    "", QtGui.QFileDialog.ShowDirsOnly);
        if str(s):
            self.update_from_directory(str(s))
        
    def update_from_directory(self, s):
        filenames = glob.glob(os.path.join(s, '*.vt'))
        
        progress = QtGui.QProgressDialog('', '', 0, len(filenames))
        progress.setWindowTitle('Adding files')
        progress.setMinimumDuration(500)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        i = 0
        for filename in filenames:
            progress.setValue(i)
            progress.setLabelText(filename)
            i += 1
            locator = FileLocator(filename)
            url = locator.to_url()
            entity = self.collection.updateVistrail(url)
            self.collection.add_to_workspace(entity)
        progress.setValue(len(filenames))
        self.collection.commit()

    def add_workspace(self):
        text, ok = QtGui.QInputDialog.getText(self, 'Create workspace',
                      'Enter new workspace name:')
        workspace = str(text).strip()
        if ok and workspace != '':
            self.collection.currentWorkspace = workspace
            if workspace not in self.collection.workspaces:
                self.collection.add_workspace(workspace)
                self.collection.commit()
            self.emit(QtCore.SIGNAL("workspaceListUpdated()"))
                
    def delete_workspace(self):
        if self.collection.currentWorkspace != 'Default':
            self.collection.delete_workspace(self.collection.currentWorkspace)
            self.collection.currentWorkspace = 'Default'
            self.collection.commit()
            self.emit(QtCore.SIGNAL("workspaceListUpdated()"))

class QWorkspaceWidget(QCollectionWidget):
    """ This class implements QCollectionWidget as a side bar browser widget
    """
    def __init__(self, collection, parent=None):
        QCollectionWidget.__init__(self, collection, parent)
        self.setColumnCount(1)
        self.setHeaderHidden(True)

    def setup_widget(self, workspace=None):
        """ Adds the items from the current workspace """
        print "self", self
        import api
        api.s = self
        print "parent"
        print "------"
        print self.parent()
        while self.topLevelItemCount():
            self.takeTopLevelItem(0)
        if workspace:
            self.collection.currentWorkspace = workspace
        for entity in self.collection.workspaces[self.collection.currentWorkspace]:
            item = QBrowserWidgetItem(entity, self)
            self.addTopLevelItem(item)
        if self.collection.currentWorkspace != 'Default':
            self.setSortingEnabled(True)
            self.sortItems(0, QtCore.Qt.AscendingOrder)

class QBrowserWidgetItem(QtGui.QTreeWidgetItem):
    def __init__(self, entity, parent=None):
        l = list(str(x) for x in entity.save())
        l.pop(0) # remove identifier
        type = l.pop(0)
        desc = l[5]
        if len(desc) > 20:
            l[5] = desc[:20] + '...'
        QtGui.QTreeWidgetItem.__init__(self, parent, [l[0]])
        self.entity = entity
        if type == '1':
            self.setIcon(0, CurrentTheme.HISTORY_ICON)
        elif type == '2':
            self.setIcon(0, CurrentTheme.PIPELINE_ICON)
        elif type == '3':
            self.setIcon(0, CurrentTheme.EXECUTE_PIPELINE_ICON)

        self.setToolTip(0, entity.url)
            
        for child in entity.children:
            l = child.save()
            if l[1] == 4:
                cache = ThumbnailCache.getInstance() #.get_directory()
                path = cache.get_abs_name_entry(l[2])
                if path:
                    self.setIcon(0, QtGui.QIcon(path))
                continue
            else:
                self.addChild(QBrowserWidgetItem(child))

    def __lt__(self, other):
        sort_col = self.treeWidget().sortColumn()
        if sort_col in set([4]):
            return int(self.text(sort_col)) < int(other.text(sort_col))
        elif sort_col in set([2,3]):
            return datetime(*strptime(str(self.text(sort_col)), '%d %b %Y %H:%M:%S')[0:6]) < datetime(*strptime(str(other.text(sort_col)), '%d %b %Y %H:%M:%S')[0:6])
        return QtGui.QTreeWidgetItem.__lt__(self, other)

    def refresh_object(self):
        Collection.getInstance().updateVistrail(self.entity.url)
        Collection.getInstance().commit()

    def remove_object(self):
        Collection.getInstance().del_from_workspace(self.entity)
        Collection.getInstance().commit()
        
class QExplorerWidget(QCollectionWidget):
    """ This class implements QCollectionWidget as a full-screen explorer widget
    """
    def __init__(self, collection, parent=None):
        QCollectionWidget.__init__(self, collection, parent)
        self.setColumnCount(6)
        self.setHeaderLabels(['name', 'user', 'mod_date', 'create_date', 'size', 'url'])

    def setup_widget(self, workspace=None):
        """ Adds the items from the current workspace """
        self.clear()
        if workspace:
            self.collection.currentWorkspace = workspace
        for entity in self.collection.workspaces[self.collection.currentWorkspace]:
            item = QExplorerWidgetItem(entity)
            self.addTopLevelItem(item)
        if self.collection.currentWorkspace != 'Default':
            self.setSortingEnabled(True)
            self.sortItems(0, QtCore.Qt.AscendingOrder)

class QExplorerWidgetItem(QtGui.QTreeWidgetItem):
    def __init__(self, entity, parent=None):
        l = list(str(x) for x in entity.save())
        l.pop(0) # remove identifier
        type = l.pop(0)
        desc = l.pop(5)
#        l.pop(7)
#        if len(desc) > 20:
#            l[5] = desc[:20] + '...'
        QtGui.QTreeWidgetItem.__init__(self, parent, l)
        self.entity = entity
        if type == '1':
            self.setIcon(0, CurrentTheme.HISTORY_ICON)
        elif type == '2':
            self.setIcon(0, CurrentTheme.PIPELINE_ICON)
        elif type == '3':
            self.setIcon(0, CurrentTheme.EXECUTE_PIPELINE_ICON)

        self.setToolTip(0, entity.url)
            
        for child in entity.children:
            l = child.save()
            if l[1] == 4:
                cache = ThumbnailCache.getInstance()
                path = cache.get_abs_name_entry(l[2])
                if path:
                    self.setIcon(0, QtGui.QIcon(path))
                continue
            else:
                self.addChild(QExplorerWidgetItem(child))

    def __lt__(self, other):
        sort_col = self.treeWidget().sortColumn()
        if sort_col in set([4]):
            return int(self.text(sort_col)) < int(other.text(sort_col))
        elif sort_col in set([2,3]):
            return datetime(*strptime(str(self.text(sort_col)), '%d %b %Y %H:%M:%S')[0:6]) < datetime(*strptime(str(other.text(sort_col)), '%d %b %Y %H:%M:%S')[0:6])
        return QtGui.QTreeWidgetItem.__lt__(self, other)

    def refresh_object(self):
        Collection.getInstance().updateVistrail(self.entity.url)
        Collection.getInstance().commit()

    def remove_object(self):
        Collection.getInstance().del_from_workspace(self.entity)
        Collection.getInstance().commit()

class QWorkspaceWindow(QToolWindow, QToolWindowInterface):
    def __init__(self, parent=None):
        QToolWindow.__init__(self, parent=parent)

        self.widget = QtGui.QWidget(self)
        self.setWidget(self.widget)
        self.workspace_list = QtGui.QComboBox()
        self.titleWidget = QtGui.QWidget(self)
        self.titleLayout = QtGui.QHBoxLayout(self)
        self.titleLayout.addWidget(QtGui.QLabel('Workspace:'), 0)
        self.titleLayout.addWidget(self.workspace_list, 1)
        self.titleWidget.setLayout(self.titleLayout)
        self.setTitleBarWidget(self.titleWidget)
        # make it possible to ignore updates during updating of workspace list
        self.updatingWorkspaceList = False
        self.connect(self.workspace_list,
                     QtCore.SIGNAL("currentIndexChanged(QString)"),
                     self.workspace_changed)
        layout = QtGui.QVBoxLayout()
#        layout.setMargin(0)
#        layout.setSpacing(5)
        self.search_box = QSearchBox(True, False, self)
        layout.addWidget(self.search_box)

        self.collection = Collection.getInstance()
        self.browser = QWorkspaceWidget(self.collection)
        layout.addWidget(self.browser)
        self.browser.setup_widget('Default')
        self.connect(self.search_box, QtCore.SIGNAL('resetSearch()'),
                     self.reset_search)
        self.connect(self.search_box, QtCore.SIGNAL('executeSearch(QString)'),
                     self.execute_search)
        self.connect(self.search_box, QtCore.SIGNAL('refineMode(bool)'),
                     self.refine_mode)
        self.connect(self.browser, QtCore.SIGNAL('workspaceListUpdated()'),
                     self.update_workspace_list)
        self.widget.setLayout(layout)
        self.update_workspace_list()
 
    def update_workspace_list(self):
        """ Updates workspace list and highlights currentWorkspace
            Keeps 'Recent files' on top
        """
        self.updatingWorkspaceList = True
        self.workspace_list.clear()
        self.workspace_list.addItem('Default')
        if 'Default' == self.browser.collection.currentWorkspace:
            self.workspace_list.setCurrentIndex(self.workspace_list.count()-1)
        locations = self.browser.collection.workspaces.keys()
        
        workspaces = [ l for l in locations \
                         if not l.startswith('file') and \
                            not l.startswith('db') and \
                            not l == 'Default']
        workspaces.sort()
        for w in workspaces:
            self.workspace_list.addItem(w)
            if w == self.browser.collection.currentWorkspace:
                self.workspace_list.setCurrentIndex(self.workspace_list.count()-1)
        self.updatingWorkspaceList = False

    def workspace_changed(self, workspace):
        if not self.updatingWorkspaceList:
            self.browser.setup_widget(str(workspace))
    
    def reset_search(self):
        self.browser.reset_search()

    def set_results(self, results):
        pass

    def execute_search(self, text):
        s = str(text)
        try:
            search = SearchCompiler(s).searchStmt
        except SearchParseError, e:
            debug.warning("Search Parse Error", str(e))
            search = None

        self.browser.run_search(search)

    def refine_mode(self, on):
        pass

class QExplorerDialog(QToolWindow, QToolWindowInterface):
    def __init__(self, parent=None):
        QToolWindow.__init__(self, parent=parent)

        self.widget = QtGui.QWidget()
        self.setWidget(self.widget)
        self.workspace_list = QtGui.QComboBox()
        self.setTitleBarWidget(self.workspace_list)
        # make it possible to ignore updates during updating of workspace list
        self.updatingWorkspaceList = False
        self.connect(self.workspace_list,
                     QtCore.SIGNAL("currentIndexChanged(QString)"),
                     self.workspace_changed)
        layout = QtGui.QVBoxLayout()
#        layout.setMargin(0)
#        layout.setSpacing(5)
        self.search_box = QSearchBox(True, False, self)
        layout.addWidget(self.search_box)

        self.collection = Collection.getInstance()
        self.browser = QExplorerWidget(self.collection, self)
        layout.addWidget(self.browser)
        self.browser.setup_widget('Recent files')
        self.connect(self.search_box, QtCore.SIGNAL('resetSearch()'),
                     self.reset_search)
        self.connect(self.search_box, QtCore.SIGNAL('executeSearch(QString)'),
                     self.execute_search)
        self.connect(self.search_box, QtCore.SIGNAL('refineMode(bool)'),
                     self.refine_mode)
        self.connect(self.browser, QtCore.SIGNAL('workspaceListUpdated()'),
                     self.update_workspace_list)
        self.widget.setLayout(layout)
        self.update_workspace_list()
 
    def update_workspace_list(self):
        """ Updates workspace list and highlights currentWorkspace
            Keeps 'Default' on top
        """
        self.updatingWorkspaceList = True
        self.workspace_list.clear()
        self.workspace_list.addItem('Default')
        if 'Default' == self.browser.collection.currentWorkspace:
            self.workspace_list.setCurrentIndex(self.workspace_list.count()-1)
        sorted_workspaces = self.browser.collection.workspaces.keys()
        if 'Default' in sorted_workspaces:
            sorted_workspaces.remove('Default')
        sorted_workspaces.sort()
        for p in sorted_workspaces:
            self.workspace_list.addItem(p)
            if p == self.browser.collection.currentWorkspace:
                self.workspace_list.setCurrentIndex(self.workspace_list.count()-1)
        self.updatingWorkspaceList = False

    def workspace_changed(self, workspace):
        if not self.updatingWorkspaceList:
            self.browser.setup_widget(str(workspace))
    
    def reset_search(self):
        self.browser.reset_search()

    def set_results(self, results):
        pass

    def execute_search(self, text):
        s = str(text)
        try:
            search = SearchCompiler(s).searchStmt
        except SearchParseError, e:
            debug.warning("Search Parse Error", str(e))
            search = None

        self.browser.run_search(search)

    def refine_mode(self, on):
        pass

if __name__ == '__main__':
    import sys
    sys.path.append('/vistrails/src/query/vistrails')
    from core.collection import Collection
    
#     vt_1 = load_vistrail(ZIPFileLocator('/vistrails/examples/spx.vt'))[0]
#     vt_2 = load_vistrail(DBLocator('vistrails.sci.utah.edu', 3306,
#                                    'vistrails', 'vistrails', '8edLj4',
#                                    obj_id=9, obj_type='vistrail'))[0]

    c = Collection('test.db')
    # c.clear()
    # e_1 = c.create_vistrail_entity(vt_1)
    # e_2 = c.create_vistrail_entity(vt_2)
    
    c.entities = {}
    c.load_entities()

    app = QtGui.QApplication(sys.argv)
    widget = QBrowserWidget(c)
    widget.setup_widget('Recent items')
    widget.show()
    sys.exit(app.exec_())
