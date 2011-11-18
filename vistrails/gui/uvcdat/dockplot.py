from PyQt4 import QtCore, QtGui
import platform
from uvcdatCommons import plotTypes
import graphicsMethodsWidgets

class DockPlot(QtGui.QDockWidget):
    def __init__(self, parent=None):
        super(DockPlot, self).__init__(parent)
        ## self.ui = Ui_DockPlot()
        ## self.ui.setupUi(self)
        self.root=parent.root
        self.setWindowTitle("Plots and Analyses")
        self.plotTree = PlotTreeWidget(self)
        self.setWidget(self.plotTree)
        ## layout = QtGui.QVBoxLayout()
        ## layout.setMargin(0)
        ## layout.setSpacing(0)
        ## layout.addWidget(self.plotTree)
        ## self.ui.mainWidget.setLayout(layout)
        self.initTree()
            
    def initTree(self):
        self.uvcdat_items={}
        for k in sorted(plotTypes.keys()):
            self.uvcdat_items[k]=QtGui.QTreeWidgetItem(None, QtCore.QStringList(k),0)
            self.plotTree.addTopLevelItem(self.uvcdat_items[k])
            for plot in plotTypes[k]:
                item = QtGui.QTreeWidgetItem(self.uvcdat_items[k], QtCore.QStringList(plot),1)
                ## Special section here for VCS GMs they have one more layer
                for m in self.plotTree.getMethods(item):
                        item2 = QtGui.QTreeWidgetItem(item, QtCore.QStringList(m),2)
        #self.plotTree.expandAll()

class PlotTreeWidget(QtGui.QTreeWidget):
    def __init__(self, parent=None):
        super(PlotTreeWidget, self).__init__(parent)
        self.header().hide()
        self.root=parent.root
        self.setRootIsDecorated(False)
        self.delegate = PlotTreeWidgetItemDelegate(self, self)
        self.setItemDelegate(self.delegate)
        self.connect(self,
                     QtCore.SIGNAL('itemPressed(QTreeWidgetItem *,int)'),
                     self.onItemPressed)

        self.connect(self,
                     QtCore.SIGNAL('itemDoubleClicked(QTreeWidgetItem *,int)'),
                     self.popupEditor)

    def onItemPressed(self, item, column):
        """ onItemPressed(item: QTreeWidgetItem, column: int) -> None
        Expand/Collapse top-level item when the mouse is pressed
        
        """
        if item and item.parent() == None:
            self.setItemExpanded(item, not self.isItemExpanded(item))
        
    def getMethods(self,item):
        plotType = item.text(0)
        analyser = item.parent().text(0)
        if analyser == "VCS":
            return self.root.canvas[0].listelements(str(plotType).lower())
        else:
            return ["default",]
        
    def popupEditor(self,item,column):
        if item.type()!=2:
            return
        name = item.text(0)
        plotType = item.parent().text(0)
        analyser = item.parent().parent().text(0)
        editorDock = QtGui.QDockWidget(self.root)
        editorDock.setWindowTitle("%s-%s-%s Graphics Method Editor" % (analyser,plotType,name))
        ## self.root.addDockWidget(QtCore.Qt.LeftDockWidgetArea,editorDock)
        save=QtGui.QPushButton("Save")
        cancel=QtGui.QPushButton("Cancel")
        w = QtGui.QFrame()
        v=QtGui.QVBoxLayout()
        h=QtGui.QHBoxLayout()
        h.addWidget(save)
        h.addWidget(cancel)
        if analyser == "VCS":
            w.editor=QtGui.QTabWidget()
            w.editor.root=self.root
            v.addWidget(w.editor)
            if editorDock.widget() is not None:
                editorDock.widget().destroy()
            if plotType == "Boxfill":
                widget = graphicsMethodsWidgets.QBoxfillEditor(w.editor,gm = str(name))
            elif plotType == "Isofill":
                widget = graphicsMethodsWidgets.QIsofillEditor(w.editor,gm = str(name))
            elif plotType == "Isoline":
                widget = graphicsMethodsWidgets.QIsolineEditor(w.editor,gm = str(name))
            elif plotType == "Meshfill":
                widget = graphicsMethodsWidgets.QMeshfillEditor(w.editor,gm = str(name))
            elif plotType == "Outfill":
                widget = graphicsMethodsWidgets.QOutfillEditor(w.editor,gm = str(name))
            elif plotType == "Outline":
                widget = graphicsMethodsWidgets.QOutlineEditor(w.editor,gm = str(name))
            elif plotType == "Scatter":
                widget = graphicsMethodsWidgets.QScatterEditor(w.editor,gm = str(name))
            elif plotType == "Taylordiagram":
                widget = graphicsMethodsWidgets.QTaylorDiagramEditor(w.editor,gm = str(name))
            elif plotType == "Vector":
                widget = graphicsMethodsWidgets.QVectorEditor(w.editor,gm = str(name))
            elif plotType == "XvsY":
                widget = graphicsMethodsWidgets.Q1DPlotEditor(w.editor,gm = str(name), type="xvsy")
            elif plotType == "Xyvsy":
                widget = graphicsMethodsWidgets.Q1DPlotEditor(w.editor,gm = str(name), type="xyvsy")
            elif plotType == "Yxvsx":
                widget = graphicsMethodsWidgets.Q1DPlotEditor(w.editor,gm = str(name), type="yxvsx")
            else:
                print "UNKWON TYPE:",plotType
            w.editor.insertTab(0,widget,"Properties")
            w.editor.setCurrentIndex(0)
            if str(name) == "default":
                widget.setEnabled(False)
                try:
                    w.editor.widget(1).widget().setEnabled(False)
                except:
                    pass
            ## Connect Button
            save.clicked.connect(widget.applyChanges)
            cancel.clicked.connect(editorDock.close)
        else:
            print "Put code to popup",analyser,"editor"
            v.addWidget(QtGui.QLabel("Maybe one day?"))
            save.clicked.connect(editorDock.close)
            cancel.clicked.connect(editorDock.close)
        v.addLayout(h)
        w.setLayout(v)
        editorDock.setWidget(w)
        editorDock.setFloating(True)
        editorDock.show()
        
class PlotTreeWidgetItemDelegate(QtGui.QItemDelegate):
    def __init__(self, view, parent):
        """ QModuleTreeWidgetItemDelegate(view: QTreeView,
                                          parent: QWidget)
                                          -> QModuleTreeWidgetItemDelegate
        Create the item delegate given the tree view
        
        """
        QtGui.QItemDelegate.__init__(self, parent)
        self.treeView = view
        self.isMac = platform.system() in ['Darwin']

    def paint(self, painter, option, index):
        """ painter(painter: QPainter, option QStyleOptionViewItem,
                    index: QModelIndex) -> None
        Repaint the top-level item to have a button-look style
        
        """
        model = index.model()
        if not model.parent(index).isValid():
            buttonOption = QtGui.QStyleOptionButton()            
            buttonOption.state = option.state
            if self.isMac:
                buttonOption.state |= QtGui.QStyle.State_Raised
            buttonOption.state &= ~QtGui.QStyle.State_HasFocus

            buttonOption.rect = option.rect
            buttonOption.palette = option.palette
            buttonOption.features = QtGui.QStyleOptionButton.None

            style = self.treeView.style()
            
            style.drawControl(QtGui.QStyle.CE_PushButton,
                              buttonOption,
                              painter,
                              self.treeView)

            branchOption = QtGui.QStyleOption()
            i = 9 ### hardcoded in qcommonstyle.cpp
            r = option.rect
            branchOption.rect = QtCore.QRect(r.left() + i / 2,
                                             r.top() + (r.height() - i) / 2,
                                             i, i)
            branchOption.palette = option.palette
            branchOption.state = QtGui.QStyle.State_Children

            if self.treeView.isExpanded(index):
                branchOption.state |= QtGui.QStyle.State_Open
                
            style.drawPrimitive(QtGui.QStyle.PE_IndicatorBranch,
                                branchOption,
                                painter, self.treeView)

            textrect = QtCore.QRect(r.left() + i * 2,
                                    r.top(),
                                    r.width() - ((5 * i) / 2),
                                    r.height())
            text = option.fontMetrics.elidedText(
                model.data(index,
                           QtCore.Qt.DisplayRole).toString(),
                QtCore.Qt.ElideMiddle,
                textrect.width())
            style.drawItemText(painter,
                               textrect,
                               QtCore.Qt.AlignCenter,
                               option.palette,
                               self.treeView.isEnabled(),
                               text)
        else:
            QtGui.QItemDelegate.paint(self, painter, option, index)

    def sizeHint(self, option, index):
        """ sizeHint(option: QStyleOptionViewItem, index: QModelIndex) -> None
        Take into account the size of the top-level button
        
        """
        return (QtGui.QItemDelegate.sizeHint(self, option, index) + 
                QtCore.QSize(2, 2))
