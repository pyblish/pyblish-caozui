try:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *


import os



import pyblish.api
reload(pyblish.api)
import pyblish.main

import logging

script_path = os.path.dirname(os.path.realpath(__file__))
_icon_root = os.path.join(script_path, 'icons')




class Check(object):
    '''
    This is what is left of the old superclass for the scene checks. Now it just
    holds a little data. Should really be deleted.
    '''
    
    not_run = 0
    ok = 1
    failure = 2
    fatal = 3


class InstanceList(QTreeWidget):
    def __init__(self, parent, instances):
        QTreeWidget.__init__(self, parent)
        #self.setHeaderHidden(True)
        self.setHeaderLabels(['Instance', 'Family'])
        self.instances = instances
        self.parent = parent

        self.setColumnCount(2)
        self.load()
        self.resizeColumnToContents(1)
        self.setColumnWidth(0, 250)
        self.itemClicked.connect(self.clicked_cb)

        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.itemSelectionChanged.connect(self.selection_changed_cb)

    def load(self):
        for instance in self.instances:
            item = QTreeWidgetItem()
            item.setText(0, instance.name)
            item.setText(1, instance.data('family'))
            item.setCheckState(0,Qt.Checked)
            item.setData(0, Qt.UserRole, instance)
            self.addTopLevelItem(item)

    def clicked_cb(self, item, column):
        if column != 0:
            # we dont want to do anything if we didnt click the first column
            return

        self.blockSignals(True)
        
        if item.checkState(column) == Qt.Checked:
            self.parent.set_instance_enabled(str(item.text(0)), True)

        elif item.checkState(column) == Qt.Unchecked:
            self.parent.set_instance_enabled(str(item.text(0)), False)

        self.blockSignals(False)

    def selection_changed_cb(self):
        selection = self.selectedItems()
        families = [s.data(0,Qt.UserRole).toPyObject().data('family') for s in selection]
        instances = [str(s.text(0)) for s in selection]
        self.parent.update_instance_selection(families, instances)




class TestListModel(QAbstractListModel):
    '''
    This Model holds all the tests to be run.

    The parameter *checks_dict* is a dictionary where the keys are already imported python package modules and the values
    is a list of strings of module names that should be loaded from that already imported python package to be search for
    instances of *checks_class* or it's subclasses to construct the final list of checks that will be loaded into
    the TestListModel.

    :param checks_dict: The dictionary of {package:['list','of','tests','modules','to','import']}
    :type checks_dict: dict
    :param checks_class: The base class of the tests to be loaded.
    :type checks_class: class

    '''
    not_run_icon = QIcon(os.path.join(_icon_root, 'pause_icon.png'))
    ok_icon = QIcon(os.path.join(_icon_root, 'ok_icon.png'))
    failure_icon = QIcon(os.path.join(_icon_root, 'alert_icon.png'))
    fatal_icon = QIcon(os.path.join(_icon_root, 'error_icon.png'))
    question_icon = QIcon(os.path.join(_icon_root, 'question_icon.png'))

    def __init__(self, context, parent=None):
        QAbstractListModel.__init__(self, parent)
        self._tests = []
        self.parent = parent
        self.context = context
        self._instances = []
        self._active_instances = []
        self.load_tests()
        

    def set_active_instance(self, instance_names):
        self._active_instances = []
        for instance in self._instances:
            if instance.name in instance_names:
                self._active_instances.append(instance)

        self.layoutChanged.emit() # this makes the widged be redrawn

    def load_tests(self):
        '''
        Loads all the tests that are specified in the *checks_dict* argument passed to the constructor.
        '''
        all_tests = []
        for plugin_type in ('validators', 'extractors', 'conformers'):
            all_tests.extend(pyblish.api.discover(type=plugin_type))

        relevant_tests = set()
        for instance in self.context:
            self._instances.append(instance)
            for plug in pyblish.api.plugins_by_family(all_tests, instance.data('family')):
                relevant_tests.add(plug)

        self._tests = list(relevant_tests)
        # now sort the tests based on order and name
        self._tests.sort(key=lambda x: (x.order, x.__name__))


    def rowCount(self, parent=None):
        rt = self.get_relevant_tests()
        return len(rt)

    def get_relevant_tests(self):
        relevant_tests = set()
        for active_instance in self._active_instances:
            for plugin in pyblish.api.plugins_by_family(self._tests, active_instance.data('family')):
                relevant_tests.add(plugin)
        res = list(relevant_tests)
        res.sort(key=lambda x: (x.order, x.__name__))
        return res

    def data(self, index, role):
        tests = self.get_relevant_tests()

        if role == Qt.ToolTipRole:
            test = tests[index.row()]

            return "Test: %s\n%s" % (test.__name__, test.families)

        if role == Qt.DecorationRole:

            row = index.row()
            test = tests[row]
            if test.override:
                icon = self.question_icon
            else:
                if test.status == Check.ok:
                    icon = self.ok_icon
                elif test.status == Check.failure:
                    if test.fixable:
                        icon = self.failure_icon
                    else:
                        icon = self.fatal_icon
                elif test.status == Check.fatal:
                    icon = self.fatal_icon
                else:
                    
                    icon = self.not_run_icon
            return icon

        if role == Qt.DisplayRole:

            row = index.row()
            test = tests[row]

            return test.__name__

        if role == Qt.UserRole:

            row = index.row()
            test = tests[row]
            return test

    def set_status(self, test, status):
        test_to_change = None
        for t in self._tests:
            if t == test:
                test_to_change = t
                break
        else:
            return

        test_to_change.status = status

        self.layoutChanged.emit()


    '''
    def setData(self, index, value, role):
        if not index.isValid() or role != Qt.BackgroundRole:
            return False

        if value is None:
            value = QColor(0,0,0,0)
        self.bg_colors[index.row()] = value
    '''


    def all_tests(self):
        return self._tests



class TestItemDelegate(QItemDelegate):
    def __init__(self, parent=None, *args):
        QItemDelegate.__init__(self, parent, *args)

    def paint(self, painter, option, index):
        painter.save()

        option.decorationPosition = QStyleOptionViewItem.Right
        

        QItemDelegate.paint(self, painter, option, index)

        painter.restore()


class LogWidget(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)

        self._buffer = ''
        layout = QVBoxLayout()
        self.text_box = QTextBrowser()
        layout.addWidget(self.text_box)

        self.setLayout(layout)

    def write(self, output):
        for letter in output:
            if letter == '\n':
                self.flush()
            self._buffer += letter

    def flush(self):
        curr_text = self.text_box.toPlainText()
        self.text_box.setText(curr_text + str(self._buffer))
        self._buffer = ''

    def info(self, text):
        curr_text = self.text_box.toPlainText()
        self.text_box.setText(curr_text + '\n' + str(text))

class SceneChecker(QDialog):
    def __init__(self, parent, window_title='czSceneChecker', button_text='Publish',
                 show_comment_field=True, require_comment=True):
        '''
        The sceneChecker dialog.

        '''
        QDialog.__init__(self, parent,  Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowMinimizeButtonHint)  # Qt.MSWindowsFixedSizeDialogHint |
        
        self.window_title = window_title
        self.setWindowTitle(window_title)


        try:
            # set up the stylesheet
            stylesheet_path = os.path.join(script_path,'darkorange.stylesheet')
            stylesheet = open(stylesheet_path)
            stylesheet_text = stylesheet.read()
            self.setStyleSheet(stylesheet_text)
        except:
            # if this dont work we dont care
            pass

        logWidget = LogWidget(self)


        pyblish_log = logging.getLogger('pyblish')
        fmt = logging.Formatter('%(levelname)s: %(message)s')
        sh = logging.StreamHandler(logWidget)
        sh.setFormatter(fmt)
        pyblish_log.addHandler(sh)

        testWidget = TestWidget(self, button_text, show_comment_field, require_comment, log=pyblish_log)

        tabWidget = QTabWidget(self)
        tabWidget.addTab(testWidget, 'Publish')
        tabWidget.addTab(logWidget, 'Log')

        layout = QVBoxLayout()
        layout.addWidget(tabWidget)

        self.setLayout(layout)
        self.resize(400,600)


class TestWidget(QWidget):
    def __init__(self, parent, button_text='Publish',
                 show_comment_field=True, require_comment=True, log=None):

        QWidget.__init__(self, parent)

        self.log = log
        self.parent = parent

        self._context = pyblish.api.Context()
        
        self.find_instances() # loads the context with instances
        if len(self._context) == 0:
            # display an error notifying the user
            #QMessageBox.critical(self, 'Instance error', 'Nothing to publish found!', QMessageBox.Ok)
            label = QLabel('Nothing to publish found')
            self.log.info('No instance found!')
            layout = QVBoxLayout()
            layout.addWidget(label)

            btn = QPushButton('Ok')

            layout.addWidget(btn)
            btn.clicked.connect(parent.close)

            self.setLayout(layout)
            return


        # create the models and delegates
        self._model = TestListModel( self._context, self)
        self._item_delegate = TestItemDelegate(self)


        # set up the window
        #self.setGeometry(200, 100, 350, 500)
        

        self.instance_list = InstanceList(self, self._context)

        # create the list view
        self.test_list_view = QListView()
        self.test_list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.test_list_view.setContextMenuPolicy(Qt.ActionsContextMenu)

        self.test_list_view.setModel(self._model)
        self.test_list_view.setItemDelegate(self._item_delegate)

        # attach the selection changed handler
        selection_model = self.test_list_view.selectionModel()
        selection_model.selectionChanged.connect(self.selection_changed_callback)

        self.optionWidget = QStackedWidget()
        blank_widget = QWidget()
        self.optionWidget.addWidget(blank_widget)
        # populate the widet
        self.option_tests = [t for t in self.test_list_view.model().all_tests() if hasattr(t, 'gui')]
        for ot in self.option_tests:
            owidget = ot.gui()
            owidget.test = ot.__name__
            self.optionWidget.addWidget(owidget)

        # create the layout
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.instance_list)
        
        # create the splitter
        self._splitter = QSplitter(self)
        self._splitter.addWidget(self.test_list_view)
        self._splitter.addWidget(self.optionWidget)
        self._splitter.setStretchFactor(1, 1)
        #self._splitter.moveSplitter(50, 1)

        main_layout.addWidget(self._splitter, 3)

        self._require_comment = require_comment
        self._show_comment = show_comment_field
        if self._show_comment:
            comment_label = QLabel('Publish comment:')
            main_layout.addWidget(comment_label)
            self._comment_field = QTextEdit()
            main_layout.addWidget(self._comment_field, 1)

        self._publish_button = QPushButton(button_text)
        main_layout.addWidget(self._publish_button, 1)
        self._publish_button.clicked.connect(self.publish)

        self.setLayout(main_layout)

        self.create_listView_context_actions()
        self.selection_changed_callback([])

        # select the first instance in instancelist
        #self.instace_list.topLevelItemCount()
        root_item = self.instance_list.invisibleRootItem()
        first_item = root_item.child(0)
        self.instance_list.setCurrentItem(first_item)


    def create_listView_context_actions(self):
        self._listView_context_actions = []

        self.runAction = QAction("run", self)
        self.runAction.triggered.connect(self.run_test)
        self.test_list_view.addAction(self.runAction)
        self._listView_context_actions.append(self.runAction)

        self.fixAction = QAction("Fix", self)
        self.fixAction.triggered.connect(self.fix_test)
        self.test_list_view.addAction(self.fixAction)
        self._listView_context_actions.append(self.fixAction)

        self.overrideAction = QAction("Override", self)
        self.overrideAction.setEnabled(True)
        self.overrideAction.triggered.connect(self.override_tests)
        self.test_list_view.addAction(self.overrideAction)
        self._listView_context_actions.append(self.overrideAction)

    def check_fixAction(self):
        pass

    def selection_changed_callback(self, selection, *args):
        selection = self.test_list_view.selectedIndexes()

        num_selected = len(selection)
        if num_selected == 0:
            self.runAction.setText('Run all tests ...')
            self.runAction.setEnabled(True)
            self.fixAction.setEnabled(False)
            self.overrideAction.setEnabled(False)

            self.optionWidget.setCurrentIndex(0)

        elif num_selected == 1:
            test = selection[0].data(Qt.UserRole)
            if hasattr(test, 'toPyObject'):
                test = test.toPyObject()

            self.runAction.setText('Run test ...')
            if test.order == 1:
                self.runAction.setEnabled(True)
            else:
                self.runAction.setEnabled(False)

            if test.fixable and test.status > Check.ok and test.order == 1:
                self.fixAction.setEnabled(True)
            else:
                self.fixAction.setEnabled(False)
            self.overrideAction.setEnabled(True)

            # show the gui
            try:
                test_index = self.option_tests.index(test)
            except ValueError:
                test_index = -1
            
            self.optionWidget.setCurrentIndex(test_index + 1)
        else:
            tests = self.get_selected_tests()
            for test in tests:
                if test.order != 1:
                    self.runAction.setEnabled(False)
                    break
            else:
                self.runAction.setEnabled(True)

            for test in tests:
                if not test.fixable and test.order == 1:
                    self.fixAction.setEnabled(False)
                    break
            else:
                self.fixAction.setEnabled(True)
            self.runAction.setText('Run tests ...')
            self.overrideAction.setEnabled(True)

    def run_test(self, *args):
        selected_tests = self.get_selected_tests()#self.test_list_view.selectedIndexes()

        if len(selected_tests) == 0:
            selected_tests = self._model.all_tests()


    
        import copy
        tmp_context = copy.copy(self._context)
        tmp_context.set_data('settings', self.get_test_settings())

        for test in selected_tests:
            if test.order == 1: # we can only run validators like this
                res = test().process(tmp_context)
                for instance, error in res:
                    if error is not None:
                        self.log.error(error)
                        self._model.set_status(test, Check.failure)
                    else:
                        self._model.set_status(test, Check.ok)

        # run this to update the context menu
        #self.selection_changed_callback(selected_tests)

    def fix_test(self, *args):
        import copy
        selected_tests = self.get_selected_tests()
        tmp_context = copy.copy(self._context)
        for test in selected_tests:
            for instance in tmp_context:
                test().fix(instance)
        self.run_test()

    def get_selected_tests(self):
        res = []
        for x in self.test_list_view.selectedIndexes():
            x_obj = x.data(Qt.UserRole)
            if hasattr(x_obj, 'toPyObject'):
                x_obj = x_obj.toPyObject()
            res.append(x_obj)
        return res

    def override_tests(self, *args):
        selected_tests = self.get_selected_tests()

        test_names = '\n'.join(['* %s' % test.__name__ for test in selected_tests])
        reason_txt, ok = QInputDialog.getText(self, 'Override', 'Give a reason for overriding the following tests:\n\n%s\n' % (test_names))
        reason_txt = str(reason_txt)
        if not ok or len(reason_txt.strip()) == 0:
            # user did not hit 'OK'
            return

        self.log.warning('OVERRIDING: %s' % reason_txt)
        cz_log.warning('Overriding [%s]: %s' % (test_names, reason_txt))

        for test in selected_tests:
            self.log.warning('overriding %s' % test.__name__)
            test.override = True

    def update_instance_selection(self, families, instance):
        model = self.test_list_view.model()
        model.set_active_instance(instance)

        self.test_list_view.update()


    def set_instance_enabled(self, instance_name, value):
        for i in self._context:
            if i.name == instance_name:
                i.set_data('publish', value)

    def find_instances(self):
        found_instances = []

        instance_plugins = pyblish.api.discover(type='selectors')
        
        for plugin in instance_plugins:
            for instance, error in plugin().process(self._context):
                if error is None:
                    if instance is not None:
                        found_instances.append(instance)
                else:
                    print error

    def get_test_settings(self):
        test_settings = {}
        for i in range(1, self.optionWidget.count()):
            wdg = self.optionWidget.widget(i)
            if hasattr(wdg, 'settings'):
                test_settings[wdg.test] = wdg.settings()
        return test_settings


    def publish(self):
        self.log.info('** STARTING PUBLISH **')
        if self._show_comment:
            comment_text = str(self._comment_field.toPlainText())

            if self._require_comment:
                if comment_text.strip() == '':
                    QMessageBox.critical(self, 'No comment', 'You must specify a publish comment!', QMessageBox.Ok)
                    return

        self._context.set_data('comment', comment_text)
        test_settings = self.get_test_settings()

        self._context.set_data('settings', test_settings)

        model = self.test_list_view.model()
        try:
            for test in model.all_tests():
                if test.override:
                    self.log.info('Skipping test [%s], overridden' % test.__name__)
                    continue
                #if issubclass(test, pyblish.api.Validator):
                res = test().process(self._context)
                for i,e in res:
                    if e is not None:
                        model.set_status(test, Check.failure)
                        raise e
                model.set_status(test, Check.ok)
        except pyblish.api.ValidationError:
            QMessageBox.critical(self, 'Validation error', 'Test [%s] failed:\n%s' % (test.__name__, str(e)), QMessageBox.Ok)
        except pyblish.api.ExtractionError:
            QMessageBox.critical(self, 'Extraction error', 'Extraction [%s] failed:\n%s' % (test.__name__, str(e)), QMessageBox.Ok)
        else:
            QMessageBox.information(self,
                                    '%s - successful!' % (self.parent.window_title),
                                    '%s successful' % self.parent.window_title,
                                    QMessageBox.Ok)
            self.parent.close()

