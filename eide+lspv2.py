import os
import sys
import json
import copy  # Added for deep copying
import concurrent.futures
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QFileDialog, QTabWidget, QDialog,
    QDialogButtonBox, QFormLayout, QLineEdit, QHBoxLayout, QPushButton,
    QListWidget, QMessageBox, QDockWidget, QTreeView, QInputDialog, QWidget,
    QMenuBar, QVBoxLayout, QAbstractItemView, QComboBox, QLabel, QTabBar,
    QSpacerItem, QSizePolicy, QPlainTextEdit, QCheckBox, QTextEdit, QSplitter,
    QListWidgetItem, QToolTip
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

# LSP server commands by file extension
owner_dbg_temp = True
if owner_dbg_temp: # turn this off if ur an end user / not a dev!!!
    LSP_SERVER_COMMANDS = {
        '.py': ['jedi-language-server'],
        '.js': ['C:\\Program Files\\nodejs\\npx.cmd', 'typescript-language-server', '--stdio'],
        '.ts': ['C:\\Program Files\\nodejs\\npx.cmd', 'typescript-language-server', '--stdio'],
        '.cpp': ['clangd'],
        '.c': ['clangd'],
        '.hpp': ['clangd'],
        '.h': ['clangd'],
        '.html': ['C:\\Program Files\\nodejs\\npx.cmd', 'html-languageserver', '--stdio'],
        '.htm': ['C:\\Program Files\\nodejs\\npx.cmd', 'html-languageserver', '--stdio'],
        '.css': ['C:\\Program Files\\nodejs\\npx.cmd', 'css-languageserver', '--stdio'],
        '.json': ['C:\\Program Files\\nodejs\\npx.cmd', 'json-languageserver', '--stdio']
    }
else:
    LSP_SERVER_COMMANDS = {'.py': ['jedi-language-server']}

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
        self.ways = copy.deepcopy(ways)

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
            wrap = True
            case_sensitive = self.case_checkbox.isChecked()
            use_regex = self.regex_checkbox.isChecked()

            found = self.editor.findFirst(
                text,
                use_regex,       # re
                case_sensitive,  # cs
                False,           # wo
                wrap,            # wrap
                True,            # forward
                False,           # line
                False            # column
            )

            self.last_search = text

        if not found:
            QMessageBox.information(self, "Not Found", "No more occurrences found.")

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
    """Code editor widget with LSP-based autocompletion and hover tooltips for errors."""

    def __init__(self, parent=None):
        super().__init__(parent)
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
        self.completion_popup.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.completion_popup.hide()

        self.completion_future = None
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.last_completion_request = None
        self.completions_active = False

        # Tooltip for errors
        # QToolTip is used statically; no need to instantiate
        self.errors_active = False
        self.current_errors = dict()  # Mapping from position to message
        self.errorid = 0

        # Enable mouse tracking to capture mouse movements
        self.setMouseTracking(True)

        # LSP attributes
        self.lsp_process = None
        self.lsp_initialized = False
        self.lsp_request_id = 0
        self.pending_requests = {}
        self.extension = None
        self.lsp_version = 1  # Track file version for LSP

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

        lexer_class = lexer_mapping.get(extension)
        if lexer_class:
            self.lexer = lexer_class(self)
        else:
            self.lexer = None
        self.setLexer(self.lexer)

    def keyPressEvent(self, event):
        if not self.completion_popup.isHidden():
            if event.key() in (Qt.Key_Down, Qt.Key_Up):
                count = self.completion_popup.count()
                if count > 0:
                    current = self.completion_popup.currentRow()
                    if event.key() == Qt.Key_Down:
                        new_index = (current + 1) % count
                        self.completion_popup.setCurrentRow(new_index)
                    else:
                        new_index = (current - 1) % count
                        self.completion_popup.setCurrentRow(new_index)
                return
            elif event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
                current_item = self.completion_popup.currentItem()
                if current_item:
                    self.insert_completion(current_item)
                self.hide_completions()
                return
            elif event.key() == Qt.Key_Escape:
                self.hide_completions()
                return
            # Otherwise, hide completions and let normal typing occur
            self.hide_completions()

        prev_text = self.text()
        super().keyPressEvent(event)
        new_text = self.text()

        # Send didChange if text changed
        if new_text != prev_text:
            self.send_lsp_did_change()

        # Trigger completion requests on alphanumeric characters or '.'
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
        while start_col > 0 and (current_line[start_col - 1].isalnum() or current_line[start_col - 1] == '_'):
            start_col -= 1

        self.setSelection(line, start_col, line, col)
        self.replaceSelectedText(completion)

    def request_completions_async(self):
        self.send_lsp_completion_request()

    def send_lsp_initialize(self, file_path):
        if not self.lsp_process:
            return
        self.lsp_request_id += 1
        req_id = self.lsp_request_id
        initialize_request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": None,
                "capabilities": {}
            }
        }
        self.send_lsp_message(initialize_request)
        self.pending_requests[req_id] = ("initialize", file_path)

    def send_lsp_did_open(self, file_path):
        if not self.lsp_process:
            return
        uri = "file://" + file_path
        text = self.text()
        did_open = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": uri,
                    "languageId": self.extension.lstrip('.') if self.extension else '',
                    "version": self.lsp_version,
                    "text": text
                }
            }
        }
        self.send_lsp_message(did_open)

    def send_lsp_did_change(self):
        if not self.lsp_process or not self.lsp_initialized:
            return
        parent_tab_widget = self.parent()
        while parent_tab_widget and not isinstance(parent_tab_widget, QTabWidget):
            parent_tab_widget = parent_tab_widget.parent()
        if parent_tab_widget:
            idx = parent_tab_widget.currentIndex()
            file_path = parent_tab_widget.tabToolTip(idx)
        else:
            file_path = None

        if not file_path:
            return

        uri = "file://" + file_path
        text = self.text()
        self.lsp_version += 1
        did_change = {
            "jsonrpc": "2.0",
            "method": "textDocument/didChange",
            "params": {
                "textDocument": {
                    "uri": uri,
                    "version": self.lsp_version
                },
                "contentChanges": [
                    {"text": text}
                ]
            }
        }
        self.send_lsp_message(did_change)

    def send_lsp_completion_request(self):
        if not self.lsp_initialized or not self.lsp_process:
            return
        line, col = self.getCursorPosition()
        # Get file path from parent tab
        parent_tab_widget = self.parent()
        while parent_tab_widget and not isinstance(parent_tab_widget, QTabWidget):
            parent_tab_widget = parent_tab_widget.parent()
        if parent_tab_widget:
            idx = parent_tab_widget.currentIndex()
            file_path = parent_tab_widget.tabToolTip(idx)
        else:
            file_path = None

        if not file_path or not os.path.isfile(file_path):
            return

        uri = "file://" + file_path
        self.lsp_request_id += 1
        req_id = self.lsp_request_id
        completion_request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "textDocument/completion",
            "params": {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": col}
            }
        }
        self.send_lsp_message(completion_request)
        self.pending_requests[req_id] = ("completion", None)

    def send_lsp_message(self, msg):
        if not self.lsp_process:
            return
        data = json.dumps(msg, ensure_ascii=False)
        message = "Content-Length: {}\r\n\r\n{}".format(len(data.encode('utf-8')), data)
        self.lsp_process.write(message.encode('utf-8'))

    def on_lsp_output(self):
        print("on_lsp_output called")
        if not self.lsp_process:
            return
        while self.lsp_process.canReadLine():
            line = self.lsp_process.readLine().data().decode('utf-8', errors='replace').rstrip('\r\n')
            print("Content-Length:" in line)
            if "Content-Length:" in line:
                print(line)
                parts = line.split("Content-Length:")
                if len(parts) > 1:
                    length_str = parts[1].strip()
                    try:
                        content_length = int(length_str) + 3
                    except ValueError:
                        # If parsing fails, ignore this line and continue
                        continue

                    # Read the blank line
                    blank_line = self.lsp_process.readLine()

                    # Now read the actual content
                    response_data = self.lsp_process.read(content_length).decode('utf-8', errors='replace')
                    self.handle_lsp_response(response_data)
            elif "Content-Type:" in line:
                # Just ignore type for now
                continue
            elif line == "":
                continue
            else:
                # Some other header line we don't care about
                continue

    def handle_lsp_response(self, data):
        try:
            response = json.loads(data)
            print(data)
        except json.JSONDecodeError:
            print("JSON parse error in handle_lsp_response. Data received:", data)
            return

        # Check if this is a response to a request we made
        if "id" in response and response["id"] in self.pending_requests:
            req_type, file_path = self.pending_requests.pop(response["id"])
            print(req_type)
            if req_type == "initialize":
                self.lsp_initialized = True
                initialized = {
                    "jsonrpc": "2.0",
                    "method": "initialized",
                    "params": {}
                }
                self.send_lsp_message(initialized)
                if file_path:
                    self.send_lsp_did_open(file_path)
            elif req_type == "completion":
                items = response.get('result', [])
                print("populating completions")
                self.populate_completions(items)
        else:
            # This might be a notification, such as publishDiagnostics
            try:
                diagnostics = response["params"].get("diagnostics", [])
                if diagnostics:
                    self.display_error(diagnostics)
            except Exception as e:
                print("Error handling response:", e)
                print(response)

    def display_error(self, diagnostics):
        print("display_error called")
        
        # Clear previous error indicators and messages if desired
        # If you want to preserve them until next update, omit these lines:
        self.clear_all_indicators()  
        self.current_errors.clear()  
        
        # Define the indicator style if not already defined
        if not self.indicatorDefined(QsciScintilla.FullBoxIndicator):
            self.indicatorDefine(
                QsciScintilla.FullBoxIndicator,
                QsciScintilla.INDIC_FULLBOX,
            )
            self.setIndicatorHoverStyle(
                QsciScintilla.FullBoxIndicator, QsciScintilla.INDIC_SQUIGGLE
            )

        for diagnostic in diagnostics:
            range_ = diagnostic.get("range", {})
            start = range_.get("start", {})
            end = range_.get("end", {})

            start_line = start.get("line", 0)
            start_col = start.get("character", 0)
            end_line = end.get("line", start_line)
            end_col = end.get("character", start_col)

            message = diagnostic.get("message", "Error")

            # Highlight the error range
            self.fillIndicatorRange(
                start_line, start_col, end_line, end_col, QsciScintilla.INDIC_SQUIGGLE
            )

            # Map each position within the range to the error message
            # We'll store a list of messages for each position to handle multiple errors
            startpos = self.positionFromLineIndex(start_line, start_col)
            endpos = self.positionFromLineIndex(end_line, end_col)
            for i in range(startpos, endpos):
                if i not in self.current_errors:
                    self.current_errors[i] = []
                self.current_errors[i].append(message)

    def mouseMoveEvent(self, event):
        # Get the mouse position
        mouse_x = event.x()
        mouse_y = event.y()

        # Get the position in the document
        pos = self.positionFromPoint(mouse_x, mouse_y)
        if pos == -1:
            QToolTip.hideText()
            self.errors_active = False
            super().mouseMoveEvent(event)
            return

        # Check if there's an error at this position
        messages = self.current_errors.get(pos, None)
        if messages:
            # If multiple messages, join them
            tooltip_text = "\n".join(messages)
            QToolTip.showText(event.globalPos(), tooltip_text, self)
            self.errors_active = True
        else:
            QToolTip.hideText()
            self.errors_active = False

        super().mouseMoveEvent(event)

    def clear_all_indicators(self):
        """Utility to clear all previously set indicators."""
        # SCI_SETINDICATORCURRENT sets which indicator we'll operate on
        # SCI_INDICATORCLEARRANGE clears indicators in the given range
        # We need to do this for the entire document. 
        length = self.length()
        for indicator_id in range(8):  # Check a range of indicator ids
            self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, indicator_id)
            self.SendScintilla(QsciScintilla.SCI_INDICATORCLEARRANGE, 0, length)

    def positionFromPoint(self, x, y):
        # Convert (x, y) to Scintilla position
        return self.SendScintilla(QsciScintilla.SCI_POSITIONFROMPOINT, x, y)


    def populate_completions(self, items):
        # If result is a dict with 'items' key, extract them
        print("populate_completions called")
        if isinstance(items, dict):
            print("items in the dict yo")
            items = items.get('items', [])
        if items is None:
            return
        self.completion_popup.clear()
        for c in items:
            label = c.get('label', '')
            self.completion_popup.addItem(label)

        if items:
            line, _ = self.getCursorPosition()
            current_pos = self.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)
            x = self.SendScintilla(QsciScintilla.SCI_POINTXFROMPOSITION, 0, current_pos)
            y = self.SendScintilla(QsciScintilla.SCI_POINTYFROMPOSITION, 0, current_pos)
            pos = self.mapToGlobal(QPoint(x, y + self.textHeight(line)))
            self.completion_popup.move(pos)
            self.completion_popup.show()
            self.completions_active = True

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if not self.completion_popup.geometry().contains(event.globalPos()):
            self.hide_completions()

    def start_lsp_server(self, file_path):
        extension = os.path.splitext(file_path)[1].lower()
        self.extension = extension
        cmd = LSP_SERVER_COMMANDS.get(extension)
        if not cmd:
            return  # No LSP for this extension

        self.lsp_process = QProcess(self)
        self.lsp_process.setProgram(cmd[0])
        self.lsp_process.setArguments(cmd[1:])
        self.lsp_process.setProcessChannelMode(QProcess.MergedChannels)
        self.lsp_process.start()

        if not self.lsp_process.waitForStarted(7500):
            print("Failed to start LSP server")
            self.lsp_process = None
            return

        self.lsp_process.readyReadStandardOutput.connect(self.on_lsp_output)
        self.lsp_process.finished.connect(lambda: print("LSP server closed"))
        self.send_lsp_initialize(file_path)

        # Set the lexer after determining the extension
        self.set_lexer_for_extension(extension)

    def indicatorDefined(self, indicator):
        """Check if an indicator is already defined."""
        return True



class CompletionsEvent(QEvent):
    def __init__(self, future):
        super().__init__(COMPLETIONS_EVENT_TYPE)
        self.future = future


class Tab(QWidget):
    """A single tab containing a code editor and associated functionalities."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.editor = Editor(self)
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

    def upd_ext(self, file_path):
        extension = os.path.splitext(file_path)[1].lower()
        self.editor.extension = extension


    # I just realised none of these issues are the cause. I have an idea. Could it be because `self.lsp_process` is not set to `tab.lsp_process` so then the `lsp_process` in `editor` is never set, thus causing all of the functions to fail? Could you fix that for me then?


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
        for action in [self.new_action, self.open_action, self.open_folder_action,
                       self.save_action, self.run_action, self.configure_run_action,
                       self.goto_line_action, self.find_action, self.replace_action,
                       self.edit_keybinds_action]:
            name = action.text()
            shortcut = self.current_bindings.get(name)
            if shortcut:
                action.setShortcut(shortcut)
            else:
                action.setShortcut("")

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
        self.terminal_dock = TerminalDock(self)
        self.terminal_dock.send_command.connect(self.handle_terminal_command)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.terminal_dock)

    def handle_terminal_command(self, cmd):
        current_tab = self.current_editor_tab()
        if current_tab is None:
            self.terminal_dock.append_output("No active tab to run commands.")
            return
        if not cmd.strip():
            return
        self.run_custom_command(cmd, current_tab)

    def run_custom_command(self, cmd, tab):
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

        # Start LSP server for this file if available
        tab.editor.start_lsp_server(fname)

    def save_file(self):
        editor_tab = self.current_editor_tab()
        if editor_tab is None:
            QMessageBox.warning(self, "No file", "No file open to save.")
            return
        idx = self.tabs.currentIndex()
        tab_text = self.tabs.tabText(idx)
        tooltip = self.tabs.tabToolTip(idx)
        new_file_saved = False
        if not tooltip or not os.path.isfile(tooltip):
            fname, _ = QFileDialog.getSaveFileName(self, "Save File", tab_text if tab_text != "Untitled" else "")
            if not fname:
                return
            new_file_saved = True
        else:
            fname = tooltip

        try:
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(editor_tab.editor.text())
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file:\n{e}")
            return

        if new_file_saved:
            # Remove the current tab
            self.tabs.removeTab(idx)
            # Create a new editor tab with the same content
            new_editor_tab = Tab()
            new_editor_tab.editor.setText(editor_tab.editor.text())
            self.tabs.addTab(new_editor_tab, fname)
            self.tabs.insertTab(idx, new_editor_tab, os.path.basename(fname))
            self.tabs.setTabToolTip(idx, fname)
            self.tabs.setCurrentIndex(idx)
        else:
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
        processed_commands = [cmd.replace("{{file}}", f'{tooltip}') for cmd in commands]
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
            if isinstance(widget, Tab):
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
