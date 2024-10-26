from PyQt5.QtGui import QFont, QColor, QIcon, QTextCharFormat, QKeySequence, QTextCursor
from PyQt5.QtWidgets import (QApplication, QActionGroup, QMainWindow, QTextEdit, QToolBar, 
                             QAction, QFileDialog, QMessageBox, QFontComboBox, QComboBox, QMenu, QWidgetAction, QLabel)
from PyQt5.QtCore import QEvent, QSize, Qt
import os
import sys
import logging
import subprocess

# Set up logging
script_name = "CaNO2.0"
log_file = os.path.join(os.path.dirname(__file__), f"{script_name}.log")

try:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
except Exception as e:
    print(f"Logging setup failed: {e}")
    sys.exit(1)

# Logger instance
logger = logging.getLogger(__name__)

# Font settings
DEFAULT_FONT_FAMILY = "Cambria"
DEFAULT_FONT_SIZE = 14
FONT_SIZES = [str(i) for i in range(8, 288, 2)]

# Highlight colors dictionary with color pairs
HIGHLIGHT_STYLES = {
    "Light Yellow / Dark Gray": {"highlight": QColor(255, 255, 204), "font": QColor(64, 64, 64)},
    "Light Blue / Dark Navy": {"highlight": QColor(204, 229, 255), "font": QColor(0, 0, 51)},
    "Light Green / Dark Green": {"highlight": QColor(204, 255, 204), "font": QColor(0, 51, 0)},
    "Light Pink / Dark Purple": {"highlight": QColor(255, 204, 229), "font": QColor(51, 0, 51)},
    "Light Orange / Dark Brown": {"highlight": QColor(255, 229, 204), "font": QColor(102, 51, 0)},
    "Light Gray / Black": {"highlight": QColor(224, 224, 224), "font": QColor(0, 0, 0)},
    "Light Purple / Dark Purple": {"highlight": QColor(229, 204, 255), "font": QColor(51, 0, 51)},
    "Light Peach / Dark Brown": {"highlight": QColor(255, 229, 204), "font": QColor(102, 51, 0)},
    "Light Teal / Dark Teal": {"highlight": QColor(204, 255, 255), "font": QColor(0, 51, 51)},
    "Pale Yellow / Dark Olive": {"highlight": QColor(255, 255, 153), "font": QColor(51, 51, 0)},
    "Mint Green / Dark Green": {"highlight": QColor(204, 255, 229), "font": QColor(0, 51, 0)}
}

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Case and Note Organizer 2.0")
        
        self.path = None
        self.current_font_family = DEFAULT_FONT_FAMILY
        self.current_font_size = DEFAULT_FONT_SIZE
        
        # Image directory
        self.images_dir = os.path.join(os.path.dirname(__file__), 'images')

        # Set up editor and UI components
        self.init_ui()
        logger.info("User interface initialized.")

    def init_ui(self):
        """Initialize main UI components."""
        self.editor = QTextEdit()
        self.setCentralWidget(self.editor)
        self.apply_default_font_settings()

        # Initialize menus and toolbars
        self.init_menus_and_toolbars()
        
        # Event filter to stop highlighting when typing starts
        self.editor.installEventFilter(self)        

    # ---------- Toolbar and Menu Initialization ----------

    def init_menus_and_toolbars(self):
        """Initialize menus and set up toolbars."""
        self.file_menu = self.menuBar().addMenu("&File")
        self.edit_menu = self.menuBar().addMenu("&Edit")
        self.format_menu = self.menuBar().addMenu("&Format")
        self.help_menu = self.menuBar().addMenu("&Help")

        # Initialize each toolbar
        self.init_file_toolbar()
        self.init_font_toolbar()
        self.init_format_toolbar()
        self.addToolBarBreak()
        self.init_edit_toolbar()
        self.init_emphasis_toolbar()
        self.init_align_toolbar()

    def init_file_toolbar(self):
        file_toolbar = QToolBar("File")
        file_toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(file_toolbar)

        new_instance_action = QAction("New", self)
        new_instance_action.setShortcut("Ctrl+N")
        new_instance_action.triggered.connect(self.run_new_instance)
        self.file_menu.addAction(new_instance_action)
        file_toolbar.addAction(new_instance_action)

        open_file_action = QAction(QIcon(os.path.join(self.images_dir, 'open_file.png')), "Open file...", self)
        open_file_action.setShortcut("Ctrl+O")
        open_file_action.triggered.connect(self.file_open)
        self.file_menu.addAction(open_file_action)
        file_toolbar.addAction(open_file_action)

        save_file_action = QAction(QIcon(os.path.join(self.images_dir, 'save.png')), "Save", self)
        save_file_action.setShortcut("Ctrl+S")
        save_file_action.triggered.connect(self.file_save)
        self.file_menu.addAction(save_file_action)
        file_toolbar.addAction(save_file_action)

        saveas_file_action = QAction(QIcon(os.path.join(self.images_dir, 'save_as.png')), "Save As...", self)
        saveas_file_action.setShortcut("Ctrl+Shift+S")
        saveas_file_action.triggered.connect(self.file_saveas)
        self.file_menu.addAction(saveas_file_action)
        file_toolbar.addAction(saveas_file_action)

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(QApplication.quit)
        self.file_menu.addAction(exit_action)

    def init_edit_toolbar(self):
        edit_toolbar = QToolBar("Edit")
        edit_toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(edit_toolbar)

        # Edit actions
        for action_name, icon_file, shortcut, method in [
            ("Undo", 'arrow-curve_left.png', QKeySequence.Undo, self.editor.undo),
            ("Redo", 'arrow-curve_right.png', QKeySequence.Redo, self.editor.redo),
            ("Cut", 'scissors.png', QKeySequence.Cut, self.editor.cut),
            ("Copy", 'document-copy.png', QKeySequence.Copy, self.editor.copy),
            ("Paste", 'clipboard-paste-document-text.png', QKeySequence.Paste, self.editor.paste)
        ]:
            action = QAction(QIcon(os.path.join(self.images_dir, icon_file)), action_name, self)
            action.setShortcut(shortcut)
            action.triggered.connect(method)
            edit_toolbar.addAction(action)
            self.edit_menu.addAction(action)

    def init_font_toolbar(self):
        font_toolbar = QToolBar("Font")
        font_toolbar.setIconSize(QSize(10, 10))
        self.addToolBar(font_toolbar)

        # Font family combobox
        self.fonts = QFontComboBox()
        self.fonts.setCurrentFont(QFont(self.current_font_family))
        self.fonts.currentFontChanged.connect(self.on_font_change)
        font_toolbar.addWidget(self.fonts)
    
        # Font size combobox
        self.fontsize = QComboBox()
        self.fontsize.addItems([str(s) for s in FONT_SIZES])
        self.fontsize.setCurrentText(str(self.current_font_size))
        self.fontsize.currentIndexChanged[str].connect(self.on_fontsize_change)
        font_toolbar.addWidget(self.fontsize)
        
    def init_format_toolbar(self):
        format_toolbar = QToolBar("Format")
        format_toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(format_toolbar)

        highlighter_action = QAction(QIcon(os.path.join(self.images_dir, 'highlighter.png')), "Highlighter", self)
        highlighter_action.triggered.connect(self.open_highlight_menu)
        format_toolbar.addAction(highlighter_action)

        clear_format_action = QAction(QIcon(os.path.join(self.images_dir, 'clear-formatting.png')), "Clear Formatting", self)
        clear_format_action.setShortcut("Esc")
        clear_format_action.triggered.connect(self.clear_formatting)
        format_toolbar.addAction(clear_format_action)
        self.format_menu.addAction(clear_format_action)

    def init_emphasis_toolbar(self): 
        """Create Emphasis toolbar for Bold, Italic, Underline, and Strikethrough."""
        emphasis_toolbar = QToolBar("Emphasis")
        emphasis_toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(emphasis_toolbar)

        # Bold action
        bold_action = QAction(QIcon(os.path.join(self.images_dir, 'bold.png')), "Bold", self)
        bold_action.setCheckable(True)
        bold_action.setShortcut(QKeySequence.Bold)
        bold_action.toggled.connect(self.toggle_bold)
        emphasis_toolbar.addAction(bold_action)
        self.format_menu.addAction(bold_action)

        # Italic action
        italic_action = QAction(QIcon(os.path.join(self.images_dir, 'italic.png')), "Italic", self)
        italic_action.setCheckable(True)
        italic_action.setShortcut(QKeySequence.Italic)
        italic_action.toggled.connect(self.toggle_italic)
        emphasis_toolbar.addAction(italic_action)
        self.format_menu.addAction(italic_action)

        # Underline action
        underline_action = QAction(QIcon(os.path.join(self.images_dir, 'underline.png')), "Underline", self)
        underline_action.setCheckable(True)
        underline_action.setShortcut(QKeySequence.Underline)
        underline_action.toggled.connect(self.toggle_underline)
        emphasis_toolbar.addAction(underline_action)
        self.format_menu.addAction(underline_action)

        # Strikethrough action
        strikethrough_action = QAction(QIcon(os.path.join(self.images_dir, 'strikethrough.png')), "Strikethrough", self)
        strikethrough_action.setCheckable(True)
        strikethrough_action.toggled.connect(self.toggle_strikethrough)
        emphasis_toolbar.addAction(strikethrough_action)
        self.format_menu.addAction(strikethrough_action)
        
    def init_align_toolbar(self):
        """Create Align toolbar for Align Left, Align Right, Center, and Justify"""
        align_toolbar = QToolBar("Align")  # Create the toolbar
        self.addToolBar(align_toolbar)  # Add the toolbar to the main window
        
        # Format menu for toolbar actions
        format_menu = self.format_menu  # Assuming `self.format_menu` is initialized in `init_menus_and_toolbars`
        
        # Alignment actions with icons and tooltips
        self.alignl_action = QAction(QIcon(os.path.join(self.images_dir, 'align-left.png')), "<- Align Left", self)
        self.alignl_action.setCheckable(True)
        self.alignl_action.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignLeft))
        align_toolbar.addAction(self.alignl_action)
        format_menu.addAction(self.alignl_action)

        self.alignc_action = QAction(QIcon(os.path.join(self.images_dir, 'align-center.png')), "-><- Align Center", self)
        self.alignc_action.setCheckable(True)
        self.alignc_action.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignCenter))
        align_toolbar.addAction(self.alignc_action)
        format_menu.addAction(self.alignc_action)

        self.alignr_action = QAction(QIcon(os.path.join(self.images_dir, 'align-right.png')), "-> Align Right", self)
        self.alignr_action.setCheckable(True)
        self.alignr_action.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignRight))
        align_toolbar.addAction(self.alignr_action)
        format_menu.addAction(self.alignr_action)

        self.alignj_action = QAction(QIcon(os.path.join(self.images_dir, 'align-justify.png')), "<--> Justify", self)
        self.alignj_action.setCheckable(True)
        self.alignj_action.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignJustify))
        align_toolbar.addAction(self.alignj_action)
        format_menu.addAction(self.alignj_action)

        # Grouping the alignment actions to make them exclusive
        format_group = QActionGroup(self)
        format_group.setExclusive(True)
        format_group.addAction(self.alignl_action)
        format_group.addAction(self.alignc_action)
        format_group.addAction(self.alignr_action)
        format_group.addAction(self.alignj_action)

    # ---------- Text Emphasis Methods ----------
    
    def toggle_bold(self, checked):
        format = QTextCharFormat()
        format.setFontWeight(QFont.Bold if checked else QFont.Normal)
        self.merge_format(format)

    def toggle_italic(self, checked):
        format = QTextCharFormat()
        format.setFontItalic(checked)
        self.merge_format(format)

    def toggle_underline(self, checked):
        format = QTextCharFormat()
        format.setFontUnderline(checked)
        self.merge_format(format)

    def toggle_strikethrough(self, checked):
        format = QTextCharFormat()
        format.setFontStrikeOut(checked)
        self.merge_format(format)

    def merge_format(self, format):
        """Apply the given QTextCharFormat to the selected text or cursor."""
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            cursor.mergeCharFormat(format)
        else:
            self.editor.setCurrentCharFormat(format)
            
    def clear_formatting(self):
        """Reset formatting to default settings, clearing all applied styles including highlight."""
        format = QTextCharFormat()
        
        # Set default font family and size
        format.setFontFamily(DEFAULT_FONT_FAMILY)
        format.setFontPointSize(DEFAULT_FONT_SIZE)

        # Clear all text formatting (bold, italic, underline, strikethrough)
        format.setFontWeight(QFont.Normal)
        format.setFontItalic(False)
        format.setFontUnderline(False)
        format.setFontStrikeOut(False)

        # Clear highlight and font color
        format.setBackground(Qt.transparent)  # Clears highlighting
        format.setForeground(Qt.black)  # Assuming default text color is black

        # Apply the reset format to selected text or cursor
        self.merge_format(format)

       
    # ---------- Highlighter Methods ----------

    def open_highlight_menu(self):
        """Display highlighter options in a menu near the cursor position."""
        highlight_menu = QMenu("Highlight Styles", self)
        for name, colors in HIGHLIGHT_STYLES.items():
            action = self.create_highlight_action(name, colors)
            highlight_menu.addAction(action)
        # Using `popup` to position menu at cursor location
        highlight_menu.popup(self.editor.viewport().mapToGlobal(self.editor.cursorRect().bottomRight()))

    def create_highlight_action(self, name, colors):
        """Creates a menu action for applying a highlight color with font color."""
        action = QWidgetAction(self)
        label = QLabel(name)
        label.setFont(QFont(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE))
        label.setStyleSheet(f"background-color: rgb({colors['highlight'].red()}, {colors['highlight'].green()}, {colors['highlight'].blue()}); "
                            f"color: rgb({colors['font'].red()}, {colors['font'].green()}, {colors['font'].blue()}); padding: 5px;")
        action.setDefaultWidget(label)
        action.triggered.connect(lambda _, colors=colors: self.apply_highlight_style(colors))
        return action

    def apply_highlight_style(self, colors):
        """Apply the selected highlight color to the current selection only."""
        format = QTextCharFormat()
        format.setBackground(colors["highlight"])
        format.setForeground(colors["font"])
        
        # Apply format only to the selected text
        self.merge_format(format)
        
    def eventFilter(self, source, event):
        """Clear formatting when ESC key is pressed."""
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                # ESC key detected, reset formatting
                self.clear_formatting()
        return super(MainWindow, self).eventFilter(source, event)

    # ---------- File Operations ----------
    def run_new_instance(self):
        subprocess.Popen([sys.executable, os.path.abspath(__file__)])

    def file_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open file", "", "Text documents (*.txt);All files (*.*)")
        if path:
            self.load_file(path)

    def file_save(self):
        if self.path:
            self.save_file(self.path)
        else:
            self.file_saveas()

    def file_saveas(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save file", "", "Text documents (*.txt)")
        if path:
            if not path.lower().endswith('.txt'):
                path += '.txt'
            self.save_file(path)

    def load_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
            self.path = path
            self.editor.setPlainText(text)
            self.update_title()
            logger.info(f"Opened file: {path}")
        except Exception as e:
            self.dialog_critical(f"Error opening file: {str(e)}")

    def save_file(self, path):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            self.path = path
            self.update_title()
            logger.info(f"File saved: {path}")
        except Exception as e:
            self.dialog_critical(f"Failed to save file: {str(e)}")

        
    # ---------- Font Management ----------

    def apply_default_font_settings(self):
        self.editor.setFont(QFont(self.current_font_family, self.current_font_size))

    def on_font_change(self, font):
        self.current_font_family = font.family()
        self.apply_current_font_settings()

    def on_fontsize_change(self, size):
        try:
            self.current_font_size = int(size)
            self.apply_current_font_settings()
        except ValueError:
            logger.error(f"Invalid font size: {size}")

    def apply_current_font_settings(self):
        cursor = self.editor.textCursor()
        format = QTextCharFormat()
        format.setFontFamily(self.current_font_family)
        format.setFontPointSize(self.current_font_size)
        if cursor.hasSelection():
            cursor.setCharFormat(format)
        else:
            self.editor.setCurrentFont(QFont(self.current_font_family, self.current_font_size))
            cursor.mergeCharFormat(format)  

    def apply_default_font_settings(self):
        self.editor.setFont(QFont(self.current_font_family, self.current_font_size))              
            
    # ---------- Helper Methods ----------            
    def dialog_critical(self, message):
        QMessageBox.critical(self, "Error", message)

    def update_title(self):
        self.setWindowTitle(f"Simple File Organizer - {os.path.basename(self.path) if self.path else 'Untitled'}")            
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
