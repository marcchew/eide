import os
import sys
import json
import jedi
import copy  # Added for deep copying
import concurrent.futures
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QFileDialog, QTabWidget, QDialog,
    QDialogButtonBox, QFormLayout, QLineEdit, QHBoxLayout, QPushButton,
    QListWidget, QMessageBox, QDockWidget, QTreeView, QInputDialog, QWidget,
    QMenuBar, QVBoxLayout, QAbstractItemView, QComboBox, QLabel, QTabBar,
    QSpacerItem, QSizePolicy, QPlainTextEdit, QCheckBox, QTextEdit, QSplitter
)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt, QDir, QModelIndex, QProcess, pyqtSignal, QPoint, QEvent
from PyQt5.Qsci import (
    QsciScintillaBase,
    QsciScintilla,
    QsciLexerPython,
    QsciLexerCPP,
    QsciLexerJava,
    QsciLexerHTML,
    QsciLexerJavaScript,
    QsciLexerCSS,
    QsciLexerRuby,
    QsciLexerSQL,
    QsciLexerXML,
    QsciLexerMarkdown,
    QsciLexerPerl,
    QsciLexerBash,
    QsciLexerCSharp,
    QsciLexerLua,
    QsciLexerJSON
)
from PyQt5.QtWidgets import QFileSystemModel



CONFIG_FILE = "run_ways.json"
KEYBINDINGS_FILE = "keybindings.json"

DEFAULT_KEYBINDINGS = {
    "New": "Ctrl+N",
    "Open File": "Ctrl+O",
    "Open Folder": "Ctrl+Shift+O",
    "Save": "Ctrl+S",
    "Run": "F5",
    "Configure Run Ways": None,
    "Go to Line": "Ctrl+G",
    "Find": "Ctrl+F",
    "Replace": "Ctrl+H",
    "Edit Keybinds": None
}

# Create a custom event type
COMPLETIONS_EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

def load_run_ways():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {}


def save_run_ways(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


def load_keybindings():
    if os.path.exists(KEYBINDINGS_FILE):
        with open(KEYBINDINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Save defaults if not exist
        save_keybindings(DEFAULT_KEYBINDINGS)
        return DEFAULT_KEYBINDINGS.copy()


def save_keybindings(data):
    with open(KEYBINDINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


class RunWaysDialog(QDialog):
    """Dialog to manage run ways configuration."""
    def __init__(self, ways, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Run Ways Configuration")
        self.setMinimumSize(600, 400)
        self.original_ways = ways
        self.ways = copy.deepcopy(ways)  # Changed to use copy.deepcopy

        main_layout = QHBoxLayout(self)

        # Left side
        left_layout = QVBoxLayout()
        self.list_ways = QListWidget()
        self.list_ways.setSelectionMode(QListWidget.SingleSelection)
        for way_name in self.ways.keys():
            self.list_ways.addItem(way_name)
        left_layout.addWidget(QLabel("Run Ways:"))
        left_layout.addWidget(self.list_ways)

        way_btn_layout = QHBoxLayout()
        self.add_way_btn = QPushButton("Add Run Way")
        self.remove_way_btn = QPushButton("Remove Run Way")
        way_btn_layout.addWidget(self.add_way_btn)
        way_btn_layout.addWidget(self.remove_way_btn)
        left_layout.addLayout(way_btn_layout)

        # Spacer
        left_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        main_layout.addLayout(left_layout, 1)

        # Right side
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Commands for Selected Run Way:"))
        self.commands_list = QListWidget()
        self.commands_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        right_layout.addWidget(self.commands_list)

        # Buttons
        cmd_btn_layout = QHBoxLayout()
        self.add_command_btn = QPushButton("Add Command")
        self.remove_command_btn = QPushButton("Remove Command")
        cmd_btn_layout.addWidget(self.add_command_btn)
        cmd_btn_layout.addWidget(self.remove_command_btn)
        right_layout.addLayout(cmd_btn_layout)

        # Spacer
        right_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        right_layout.addWidget(buttons)
        main_layout.addLayout(right_layout, 2)

        # Connections
        self.list_ways.currentItemChanged.connect(self.load_selected_way)
        self.add_way_btn.clicked.connect(self.add_run_way)
        self.remove_way_btn.clicked.connect(self.remove_run_way)
        self.add_command_btn.clicked.connect(self.add_command)
        self.remove_command_btn.clicked.connect(self.remove_command)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        if self.list_ways.count() > 0:
            self.list_ways.setCurrentRow(0)
        else:
            self.add_run_way()

    def add_run_way(self):
        way_name, ok = QInputDialog.getText(self, "Add Run Way", "Enter the name for the new run way:")
        if ok and way_name:
            way_name = way_name.strip()
            if way_name in self.ways:
                QMessageBox.warning(self, "Duplicate Name", f"The run way '{way_name}' already exists.")
                return
            self.ways[way_name] = []
            self.list_ways.addItem(way_name)
            self.list_ways.setCurrentRow(self.list_ways.count() - 1)

    def remove_run_way(self):
        current_item = self.list_ways.currentItem()
        if current_item:
            way_name = current_item.text()
            reply = QMessageBox.question(
                self, "Remove Run Way",
                f"Are you sure you want to remove the run way '{way_name}'?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.ways.pop(way_name, None)
                self.list_ways.takeItem(self.list_ways.row(current_item))
                self.commands_list.clear()
        else:
            QMessageBox.information(self, "No Selection", "Please select a run way to remove.")

    def load_selected_way(self):
        item = self.list_ways.currentItem()
        if item is None:
            self.commands_list.clear()
            return
        way_name = item.text()
        self.commands_list.clear()
        for cmd in self.ways.get(way_name, []):
            self.commands_list.addItem(cmd)

    def add_command(self):
        current_item = self.list_ways.currentItem()
        if current_item is None:
            QMessageBox.information(self, "No Run Way Selected", "Please select a run way to add commands.")
            return
        way_name = current_item.text()
        cmd, ok = QInputDialog.getText(self, "Add Command", "Enter the command (use {{file}} for file):")
        if ok and cmd:
            cmd = cmd.strip()
            if not cmd:
                QMessageBox.warning(self, "Invalid Command", "Command cannot be empty.")
                return
            self.ways[way_name].append(cmd)
            self.commands_list.addItem(cmd)

    def remove_command(self):
        current_item = self.list_ways.currentItem()
        if current_item is None:
            QMessageBox.information(self, "No Run Way Selected", "Please select a run way to remove commands.")
            return
        selected_commands = self.commands_list.selectedItems()
        if not selected_commands:
            QMessageBox.information(self, "No Selection", "Please select a command to remove.")
            return
        way_name = current_item.text()
        for item in selected_commands:
            cmd = item.text()
            self.ways[way_name].remove(cmd)
            self.commands_list.takeItem(self.commands_list.row(item))

    def accept(self):
        save_run_ways(self.ways)
        self.original_ways.clear()
        self.original_ways.update(self.ways)
        super().accept()


class RunDialog(QDialog):
    """Dialog to select a run way for execution."""
    def __init__(self, ways, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Run")
        self.setMinimumSize(300, 100)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Select a run way:"))
        self.combo = QComboBox()
        self.combo.addItems(ways)
        layout.addWidget(self.combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def selected_way(self):
        return self.combo.currentText()


class FindReplaceDialog(QDialog):
    """Dialog for finding and replacing text in the editor."""
    def __init__(self, editor, parent=None, replace_mode=False):
        super().__init__(parent)
        self.last_search = ""
        self.editor = editor
        self.replace_mode = replace_mode
        self.setWindowTitle("Find and Replace" if replace_mode else "Find")
        self.setMinimumSize(400, 150)
        layout = QFormLayout(self)

        self.find_input = QLineEdit()
        layout.addRow("Find:", self.find_input)

        if replace_mode:
            self.replace_input = QLineEdit()
            layout.addRow("Replace:", self.replace_input)

        self.regex_checkbox = QCheckBox("Use Regex")
        self.case_checkbox = QCheckBox("Case Sensitive")
        opts_layout = QHBoxLayout()
        opts_layout.addWidget(self.regex_checkbox)
        opts_layout.addWidget(self.case_checkbox)
        layout.addRow(opts_layout)

        btn_layout = QHBoxLayout()
        self.find_btn = QPushButton("Find Next")
        self.find_btn.clicked.connect(self.find_next)
        btn_layout.addWidget(self.find_btn)

        if replace_mode:
            self.replace_btn = QPushButton("Replace")
            self.replace_btn.clicked.connect(self.replace)
            self.replace_all_btn = QPushButton("Replace All")
            self.replace_all_btn.clicked.connect(self.replace_all)
            btn_layout.addWidget(self.replace_btn)
            btn_layout.addWidget(self.replace_all_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)
        layout.addRow(btn_layout)

        self.setLayout(layout)

    def find_next(self):
        text = self.find_input.text()
        if not text:
            QMessageBox.information(self, "Empty Search", "Please enter text to find.")
            return
        elif text == self.last_search:
            found = self.editor.findNext()
        else:
            # Enable wrapping to allow searching beyond the current cursor position
            wrap = True

            # Retrieve the current search settings from the UI
            case_sensitive = self.case_checkbox.isChecked()
            use_regex = self.regex_checkbox.isChecked()

            # Perform the search starting from the current cursor position
            found = self.editor.findFirst(
                text,
                use_regex,       # re
                case_sensitive,  # cs
                False,           # wo (whole word)
                wrap,            # wrap
                True,            # forward
                False,           # line
                False            # column
            )

            self.last_search = text

        if not found:
            QMessageBox.information(self, "Not Found", "No more occurrences found.")
        else:
            pass


    def replace(self):
        if self.editor.hasSelectedText():
            self.editor.replaceSelectedText(self.replace_input.text())
        self.find_next()

    def replace_all(self):
        count = 0
        pattern = self.find_input.text()
        replace_text = self.replace_input.text()
        case = self.case_checkbox.isChecked()
        regex = self.regex_checkbox.isChecked()

        if not pattern:
            QMessageBox.information(self, "Empty Search", "Please enter text to find.")
            return

        # Move cursor to start
        self.editor.setCursorPosition(0, 0)
        while self.editor.findFirst(pattern, False, False, False, case, regex):
            self.editor.replaceSelectedText(replace_text)
            count += 1
        QMessageBox.information(self, "Replace All", f"Replaced {count} occurrences.")


class KeybindingsDialog(QDialog):
    """Dialog to edit keybindings."""
    def __init__(self, bindings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Keybinds")
        self.bindings = dict(bindings)  # copy
        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        for action_name, shortcut in self.bindings.items():
            sc = shortcut if shortcut else ""
            self.list_widget.addItem(f"{action_name}: {sc}")
        layout.addWidget(self.list_widget)

        self.edit_btn = QPushButton("Edit Selected")
        self.edit_btn.clicked.connect(self.edit_selected)
        layout.addWidget(self.edit_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def edit_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        text = item.text()
        if ":" not in text:
            return
        action_name, current_shortcut = text.split(":", 1)
        action_name = action_name.strip()
        current_shortcut = current_shortcut.strip()
        new_shortcut, ok = QInputDialog.getText(
            self, "Edit Shortcut",
            f"Enter new shortcut for '{action_name}':",
            text=current_shortcut
        )
        if ok:
            # Allow empty to clear shortcut
            self.bindings[action_name] = new_shortcut.strip() if new_shortcut.strip() else None
            sc = new_shortcut.strip() if new_shortcut.strip() else ""
            item.setText(f"{action_name}: {sc}")

    def accept(self):
        super().accept()


class TerminalDock(QDockWidget):
    """A dockable terminal allowing user input and displaying output."""
    send_command = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Terminal", parent)
        self.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

        main_widget = QWidget()
        self.setWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Courier New", 10))
        layout.addWidget(self.output)

        self.input = QLineEdit()
        self.input.returnPressed.connect(self.handle_input)
        layout.addWidget(self.input)

    def handle_input(self):
        cmd = self.input.text()
        if cmd.strip() == "":
            return
        self.output.append(f"> {cmd}")
        self.send_command.emit(cmd)
        self.input.clear()

    def append_output(self, text):
        self.output.append(text)


class Editor(QsciScintilla):
    """Code editor widget with syntax highlighting."""
    def __init__(self, parent=None):
        super().__init__(parent)
        # Removed self.setUtf8(True) as it's deprecated and can cause issues.

        # Use a known monospaced font
        font = QFont("Courier New", 10)
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        self.setFont(font)
        self.setMarginsFont(font)

        self.setMargins(1)
        self.setMarginType(0, QsciScintilla.NumberMargin)
        self.setMarginLineNumbers(0, True)
        self.setMarginWidth(0, '00000')
        self.setTabWidth(4)
        self.setWrapMode(QsciScintilla.WrapNone)
        self.setEdgeMode(QsciScintilla.EdgeNone)
        self.setFolding(QsciScintilla.NoFoldStyle)

        self.lexer = None

        # Completion popup
        self.completion_popup = QListWidget()
        # Make sure popup doesn't steal focus
        self.completion_popup.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.completion_popup.hide()

        self.completion_future = None
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.last_completion_request = None
        self.completions_active = False


    def set_lexer_for_extension(self, extension):
        extension = extension.lower()

        lexer_mapping = {
            '.py': QsciLexerPython,
            '.cpp': QsciLexerCPP,
            '.c': QsciLexerCPP,
            '.h': QsciLexerCPP,
            '.hpp': QsciLexerCPP,
            '.java': QsciLexerJava,
            '.js': QsciLexerJavaScript,
            '.html': QsciLexerHTML,
            '.htm': QsciLexerHTML,
            '.css': QsciLexerCSS,
            '.php': QsciLexerHTML,
            '.rb': QsciLexerRuby,
            '.sql': QsciLexerSQL,
            '.xml': QsciLexerXML,
            '.md': QsciLexerMarkdown,
            '.markdown': QsciLexerMarkdown,
            '.pl': QsciLexerPerl,
            '.sh': QsciLexerBash,
            '.bash': QsciLexerBash,
            '.cs': QsciLexerCSharp,
            '.lua': QsciLexerLua,
            '.json': QsciLexerJSON
        }

        # Retrieve the lexer class based on the extension
        lexer_class = lexer_mapping.get(extension)

        if lexer_class:
            # Instantiate the lexer
            self.lexer = lexer_class(self)
        else:
            self.lexer = None

        # Apply the lexer to the editor
        self.setLexer(self.lexer)

    def keyPressEvent(self, event):
        # If the popup is visible, handle navigation keys
        print("keypress")
        if not self.completion_popup.isHidden():
            if event.key() in (Qt.Key_Down, Qt.Key_Up):
                # Navigate completions
                count = self.completion_popup.count()
                if count == 0:
                    pass
                else:
                    current = self.completion_popup.currentRow()
                    if event.key() == Qt.Key_Down:
                        new_index = (current + 1) % count
                        self.completion_popup.setCurrentRow(new_index)
                    else:
                        new_index = (current - 1) % count
                        self.completion_popup.setCurrentRow(new_index)
                return
            elif event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
                # Insert selected completion
                current_item = self.completion_popup.currentItem()
                if current_item:
                    self.insert_completion(current_item)
                self.hide_completions()
                return
            elif event.key() == Qt.Key_Escape:
                # Hide completions
                self.hide_completions()
                return
            # Otherwise, let normal typing continue, but hide completions if needed
            self.hide_completions()

        super().keyPressEvent(event)

        # After handling normal typing, trigger completions
        # Restrict to certain keys or always trigger after a short delay
        if event.text().isalnum() or event.text() == '.':
            self.request_completions_async()

    def hide_completions(self):
        self.completion_popup.hide()
        self.completion_popup.clear()
        self.completions_active = False

    def insert_completion(self, item):
        if not item:
            return
        completion = item.text()

        line, col = self.getCursorPosition()
        current_line = self.text(line)
        start_col = col
        # Move backwards to find where the current word starts
        while start_col > 0 and (current_line[start_col-1].isalnum() or current_line[start_col-1] == '_'):
            start_col -= 1

        # Remove the existing partial word
        self.setSelection(line, start_col, line, col)
        self.replaceSelectedText(completion)

    def request_completions_async(self):
        if self.completion_future and not self.completion_future.done():
            # Cancel or just let it run and ignore its result:
            # We cannot truly cancel jedi easily, but we can ignore old results.
            pass

        text = self.text()
        line, col = self.getCursorPosition()
        self.last_completion_request = (text, line, col)
        
        def get_completions():
            print("getting completions")
            try:
                script = jedi.Script(code=text, path=None)
                return script.complete(column=col, line=line+1)
            except Exception as e:
                print(e)
                return []
            
        self.completion_future = self.executor.submit(get_completions)
        self.completion_future.add_done_callback(self.on_completions_ready)

    def on_completions_ready(self, future):
        # This callback is called in a thread, so we cannot directly update the GUI.
        # Instead, post a custom event to the editor widget.
        QApplication.instance().postEvent(self, CompletionsEvent(future))

    def customEvent(self, event):
        if event.type() == COMPLETIONS_EVENT_TYPE:
            # Handle the completions here
            self.handle_completions(event.future)
        else:
            super().customEvent(event)

    def handle_completions(self, future):
        # This is now the main thread context
        completions = future.result()
        if not completions:
            self.hide_completions()
            return

        self.populate_completions(completions)

    def populate_completions(self, completions):
        self.completion_popup.clear()
        for c in completions:
            self.completion_popup.addItem(c.name)
        self.completion_popup.setCurrentRow(0)

        line, _ = self.getCursorPosition()
        x = self.SendScintilla(QsciScintilla.SCI_POINTXFROMPOSITION, 0, self.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS))
        y = self.SendScintilla(QsciScintilla.SCI_POINTYFROMPOSITION, 0, self.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS))
        pos = self.mapToGlobal(QPoint(x, y + self.textHeight(line)))
        self.completion_popup.move(pos)
        self.completion_popup.show()
        self.completions_active = True
        self.setFocus()  # Ensure editor keeps focus for typing

    # Mouse click on item inserts completion
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        # If clicking outside, hide completions
        if not self.completion_popup.geometry().contains(event.globalPos()):
            self.hide_completions()


class CompletionsEvent(QEvent):
    def __init__(self, future):
        super().__init__(COMPLETIONS_EVENT_TYPE)
        self.future = future

class Tab(QWidget):
    """A single tab containing a code editor and associated functionalities."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.editor = Editor()
        self.layout.addWidget(self.editor)

        self.process = None
        self.modified = False
        self.editor.textChanged.connect(self.on_text_changed)

    def on_text_changed(self):
        if not self.modified:
            self.modified = True
            parent = self.parent()
            while parent and not isinstance(parent, QTabWidget):
                parent = parent.parent()
            if parent:
                index = parent.indexOf(self)
                if index != -1:
                    current_title = parent.tabText(index)
                    if not current_title.endswith("*"):
                        parent.setTabText(index, current_title + "*")

    def mark_saved(self):
        if self.modified:
            self.modified = False
            parent = self.parent()
            while parent and not isinstance(parent, QTabWidget):
                parent = parent.parent()
            if parent:
                index = parent.indexOf(self)
                if index != -1:
                    current_title = parent.tabText(index)
                    if current_title.endswith("*"):
                        parent.setTabText(index, current_title[:-1])

    def run_command(self, cmd, terminal):
        if self.process and self.process.state() == QProcess.Running:
            terminal.append_output("A process is already running.")
            return

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)

        if sys.platform.startswith('win'):
            self.process.setProgram("cmd.exe")
            self.process.setArguments(["/c", cmd])
        else:
            self.process.setProgram("bash")
            self.process.setArguments(["-c", cmd])

        self.process.readyReadStandardOutput.connect(lambda: self.handle_stdout(terminal))
        self.process.readyReadStandardError.connect(lambda: self.handle_stderr(terminal))
        self.process.finished.connect(lambda exitCode, exitStatus: self.process_finished(exitCode, exitStatus, terminal))

        self.process.start()

        if not self.process.waitForStarted():
            terminal.append_output("Failed to start the process.")

        terminal.append_output(f"$ {cmd}")

    def handle_stdout(self, terminal):
        data = self.process.readAllStandardOutput().data().decode()
        terminal.append_output(data)

    def handle_stderr(self, terminal):
        data = self.process.readAllStandardError().data().decode()
        terminal.append_output(data)

    def process_finished(self, exitCode, exitStatus, terminal):
        terminal.append_output(f"\nProcess finished with exit code {exitCode}.")
        self.process = None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("eIDE v1.0.0 alpha (PyQT)")
        self.setMinimumSize(1000, 600)

        self.run_ways = load_run_ways()
        self.current_bindings = load_keybindings()

        self.tabs = QTabWidget()
        self.tabs.setTabBar(CustomTabBar())
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.tabBarClicked.connect(self.on_tab_bar_clicked)
        self.setCentralWidget(self.tabs)

        self.create_actions()
        self.apply_keybindings()
        self.create_menus()
        self.create_dock()

        self.create_new_tab()
        self.add_plus_tab()

        # Create Terminal Dock
        self.create_terminal_dock()

    def create_actions(self):
        self.new_action = QAction("New", self)
        self.new_action.triggered.connect(self.create_new_tab)

        self.open_action = QAction("Open File", self)
        self.open_action.triggered.connect(self.open_file)

        self.open_folder_action = QAction("Open Folder", self)
        self.open_folder_action.triggered.connect(self.open_folder)

        self.save_action = QAction("Save", self)
        self.save_action.triggered.connect(self.save_file)

        self.run_action = QAction("Run", self)
        self.run_action.triggered.connect(self.run_code)

        self.configure_run_action = QAction("Configure Run Ways", self)
        self.configure_run_action.triggered.connect(self.configure_run_ways)

        self.goto_line_action = QAction("Go to Line", self)
        self.goto_line_action.triggered.connect(self.goto_line)

        self.find_action = QAction("Find", self)
        self.find_action.triggered.connect(self.show_find_dialog)

        self.replace_action = QAction("Replace", self)
        self.replace_action.triggered.connect(self.show_replace_dialog)

        self.edit_keybinds_action = QAction("Edit Keybinds", self)
        self.edit_keybinds_action.triggered.connect(self.edit_keybinds)

    def apply_keybindings(self):
        # Assign shortcuts from current_bindings
        for action in [self.new_action, self.open_action, self.open_folder_action,
                       self.save_action, self.run_action, self.configure_run_action,
                       self.goto_line_action, self.find_action, self.replace_action,
                       self.edit_keybinds_action]:
            name = action.text()
            shortcut = self.current_bindings.get(name)
            if shortcut:
                action.setShortcut(shortcut)
            else:
                action.setShortcut("")  # clear any default

    def create_menus(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.open_folder_action)
        file_menu.addAction(self.save_action)

        run_menu = menubar.addMenu("Run")
        run_menu.addAction(self.run_action)
        run_menu.addAction(self.configure_run_action)

        edit_menu = menubar.addMenu("Edit")
        edit_menu.addAction(self.goto_line_action)
        edit_menu.addAction(self.find_action)
        edit_menu.addAction(self.replace_action)

        preferences_menu = menubar.addMenu("Preferences")
        preferences_menu.addAction(self.edit_keybinds_action)

    def create_dock(self):
        self.dock = QDockWidget("File Browser", self)
        self.dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.fs_model = QFileSystemModel()
        self.fs_model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)
        self.fs_model.setRootPath(QDir.currentPath())

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.fs_model)
        self.tree_view.doubleClicked.connect(self.on_file_double_clicked)
        self.tree_view.setRootIndex(self.fs_model.index(QDir.currentPath()))
        self.tree_view.setAnimated(True)
        self.tree_view.setIndentation(20)
        self.tree_view.setSortingEnabled(True)

        self.dock.setWidget(self.tree_view)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock)

    def create_terminal_dock(self):
        """Creates a separate dock for the terminal."""
        self.terminal_dock = TerminalDock(self)
        self.terminal_dock.send_command.connect(self.handle_terminal_command)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.terminal_dock)

    def handle_terminal_command(self, cmd):
        """Handles commands entered in the terminal."""
        current_tab = self.current_editor_tab()
        if current_tab is None:
            self.terminal_dock.append_output("No active tab to run commands.")
            return
        if not cmd.strip():
            return
        # Here you can implement custom command handling if needed
        # For now, we'll treat it as a run command
        self.run_custom_command(cmd, current_tab)

    def run_custom_command(self, cmd, tab):
        """Runs a custom command entered in the terminal."""
        tab.run_command(cmd, self.terminal_dock)

    def on_file_double_clicked(self, index):
        if not index.isValid():
            return
        path = self.fs_model.filePath(index)
        if os.path.isfile(path):
            self.open_specific_file(path)
        else:
            if self.tree_view.isExpanded(index):
                self.tree_view.collapse(index)
            else:
                self.tree_view.expand(index)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Folder", QDir.currentPath())
        if folder:
            self.fs_model.setRootPath(folder)
            self.tree_view.setRootIndex(self.fs_model.index(folder))

    def create_new_tab(self):
        tab = Tab()
        plus_index = self.find_plus_tab()
        if plus_index >= 0:
            self.tabs.insertTab(plus_index, tab, "Untitled")
            self.tabs.setCurrentIndex(plus_index)
        else:
            self.tabs.addTab(tab, "Untitled")
            self.tabs.setCurrentWidget(tab)
        self.tabs.tabBar().updateTabCloseButton(self.tabs.currentIndex())

    def add_plus_tab(self):
        plus_tab = QWidget()
        self.tabs.addTab(plus_tab, "+")
        self.tabs.setTabToolTip(self.tabs.count()-1, "Add new tab")
        self.tabs.tabBar().updateTabCloseButton(self.tabs.count()-1)

    def find_plus_tab(self):
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == "+":
                return i
        return -1

    def on_tab_bar_clicked(self, index):
        if self.tabs.tabText(index) == "+":
            self.create_new_tab()

    def open_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open File", QDir.currentPath())
        if fname:
            self.open_specific_file(fname)

    def open_specific_file(self, fname):
        try:
            with open(fname, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open file:\n{e}")
            return
        tab = Tab()
        tab.editor.setText(text)
        extension = os.path.splitext(fname)[1]
        tab.editor.set_lexer_for_extension(extension)
        plus_index = self.find_plus_tab()
        if plus_index >= 0:
            self.tabs.insertTab(plus_index, tab, os.path.basename(fname))
            self.tabs.setTabToolTip(plus_index, fname)
            self.tabs.setCurrentIndex(plus_index)
        else:
            idx = self.tabs.addTab(tab, os.path.basename(fname))
            self.tabs.setTabToolTip(idx, fname)
            self.tabs.setCurrentIndex(idx)
        self.tabs.tabBar().updateTabCloseButton(self.tabs.currentIndex())
        tab.mark_saved()

    def save_file(self):
        editor_tab = self.current_editor_tab()
        if editor_tab is None:
            QMessageBox.warning(self, "No file", "No file open to save.")
            return
        idx = self.tabs.currentIndex()
        tab_text = self.tabs.tabText(idx)
        tooltip = self.tabs.tabToolTip(idx)
        if not tooltip or not os.path.isfile(tooltip):
            fname, _ = QFileDialog.getSaveFileName(self, "Save File", tab_text if tab_text != "Untitled" else "")
            if not fname:
                return
        else:
            fname = tooltip

        try:
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(editor_tab.editor.text())
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file:\n{e}")
            return
        self.tabs.setTabText(idx, os.path.basename(fname))
        self.tabs.setTabToolTip(idx, fname)
        editor_tab.mark_saved()
        QMessageBox.information(self, "Saved", f"File saved successfully to {fname}")

    def current_editor_tab(self):
        widget = self.tabs.currentWidget()
        if isinstance(widget, Tab):
            return widget
        return None

    def configure_run_ways(self):
        dialog = RunWaysDialog(self.run_ways, self)
        if dialog.exec_() == QDialog.Accepted:
            self.run_ways = load_run_ways()

    def run_code(self):
        ways = list(self.run_ways.keys())
        if not ways:
            QMessageBox.warning(self, "No ways configured", "No run ways configured. Configure them first.")
            return

        dialog = RunDialog(ways, self)
        if dialog.exec_() == QDialog.Accepted:
            way = dialog.selected_way()
        else:
            return
        commands = self.run_ways.get(way, [])

        if not commands:
            QMessageBox.information(self, "No Commands", "The selected run way has no commands.")
            return

        current_tab = self.current_editor_tab()
        if current_tab is None:
            QMessageBox.warning(self, "No file", "No file open to run.")
            return
        idx = self.tabs.currentIndex()
        tooltip = self.tabs.tabToolTip(idx)
        if not tooltip or not os.path.isfile(tooltip):
            fname, _ = QFileDialog.getSaveFileName(self, "Save before run", "Untitled.py")
            if not fname:
                return
            try:
                with open(fname, 'w', encoding='utf-8') as f:
                    f.write(current_tab.editor.text())
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file:\n{e}")
                return
            self.tabs.setTabText(idx, os.path.basename(fname))
            self.tabs.setTabToolTip(idx, fname)
            tooltip = fname
            current_tab.mark_saved()
        print(tooltip)
        processed_commands = [cmd.replace("{{file}}", f'{tooltip}') for cmd in commands]
        print(processed_commands)
        if sys.platform.startswith('win'):
            separator = ' && '
        else:
            separator = ' ; '

        combined_cmd = separator.join(processed_commands)
        current_tab.run_command(combined_cmd, self.terminal_dock)

    def close_tab(self, index):
        if self.tabs.tabText(index) == "+":
            return
        widget = self.tabs.widget(index)
        if widget:
            if widget.process and widget.process.state() == QProcess.Running:
                widget.process.kill()
            self.tabs.removeTab(index)
            widget.deleteLater()

    def closeEvent(self, event):
        unsaved = []
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, Tab):
                if widget.modified:
                    unsaved.append(self.tabs.tabText(i).rstrip("*"))
        if unsaved:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f"The following tabs have unsaved changes:\n" + "\n".join(unsaved) +
                "\n\nDo you want to exit without saving?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
        event.accept()

    def goto_line(self):
        editor_tab = self.current_editor_tab()
        if editor_tab is None:
            QMessageBox.information(self, "No Editor", "No editor is currently open.")
            return
        line_num, ok = QInputDialog.getInt(self, "Go to Line", "Enter line number:", 1, 1)
        if ok:
            editor_tab.editor.setCursorPosition(line_num - 1, 0)

    def show_find_dialog(self):
        editor_tab = self.current_editor_tab()
        if editor_tab:
            dialog = FindReplaceDialog(editor_tab.editor, self, replace_mode=False)
            dialog.exec_()

    def show_replace_dialog(self):
        editor_tab = self.current_editor_tab()
        if editor_tab:
            dialog = FindReplaceDialog(editor_tab.editor, self, replace_mode=True)
            dialog.exec_()

    def edit_keybinds(self):
        dialog = KeybindingsDialog(self.current_bindings, self)
        if dialog.exec_() == QDialog.Accepted:
            new_bindings = dialog.bindings
            save_keybindings(new_bindings)
            self.current_bindings = load_keybindings()
            self.apply_keybindings()


class CustomTabBar(QTabBar):
    """Custom tab bar with close buttons."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)

    def tabInserted(self, index):
        super().tabInserted(index)
        self.updateTabCloseButton(index)

    def updateTabCloseButton(self, index):
        if self.tabText(index) == "+":
            self.setTabButton(index, QTabBar.RightSide, None)
        else:
            if not self.tabButton(index, QTabBar.RightSide):
                self.setTabButton(index, QTabBar.RightSide, self.close_icon_button())

    def close_icon_button(self):
        btn = QPushButton()
        btn.setFixedSize(16, 16)
        btn.setStyleSheet("border: none;")
        btn.setIcon(QIcon.fromTheme("window-close"))
        btn.setToolTip("Close Tab")
        return btn


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1000, 600)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
