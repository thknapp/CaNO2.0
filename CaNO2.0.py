import sys
import os
import json
import logging
import subprocess
import win32con 
import win32gui 
import ctypes
from PyQt6.QtGui import (
    QGuiApplication, QBitmap, QFont, QColor, QIcon, QTextCharFormat, QAction, QActionGroup, QTextListFormat,
    QTextCursor, QPixmap, QPainter, QPen, QTextDocument,
    QTextImageFormat
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QToolBar, QComboBox, QFontComboBox, QSizePolicy,
    QMenu, QWidgetAction, QLabel, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QTabWidget, QFileDialog, QMessageBox, QInputDialog
)
from PyQt6.QtCore import (
    QEvent, Qt, QSize, QBuffer, QByteArray, QPoint, QRect, pyqtSignal, QDateTime, QUrl, QTimer
)

import pytesseract
from PIL import Image
from io import BytesIO 
from spellchecker import SpellChecker

# Constants for application configuration
script_name = "CaNO2.0"
settings_dir = os.path.join(os.getenv('APPDATA'), script_name)
os.makedirs(settings_dir, exist_ok=True)
settings_file = os.path.join(settings_dir, f"{script_name}-settings.json")
custom_dict_path = os.path.join(settings_dir, "custom_dictionary.json")

# Set up logging
log_file = os.path.join(os.path.dirname(__file__), f"{script_name}.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Spell Checker initialization
spell = SpellChecker()
# Load custom dictionary
if os.path.exists(custom_dict_path):
    with open(custom_dict_path, 'r') as f:
        custom_words = json.load(f)
else:
    custom_words = []

# Add custom words to spell checker
spell.word_frequency.load_words(custom_words)

# Function to minimize the console
#def minimize_console():
#    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
#    if hwnd != 0:
#        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

# Relaunch script minimized if not already minimized
#def relaunch_minimized():
#    if sys.platform == "win32" and "--minimized" not in sys.argv:
#        subprocess.Popen(["python", __file__, "--minimized"], creationflags=win32con.SW_HIDE)
#        sys.exit()

# Relaunch if not minimized
#if "--minimized" not in sys.argv:
#    relaunch_minimized()
#else:
#    sys.argv.remove("--minimized")
#    minimize_console()  # Minimize console window after relaunch

# Load settings from JSON
def load_settings():
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                return json.load(f) or {}  # Return empty dict if the file is empty
        except json.JSONDecodeError:
            logger.warning("Settings file is empty or invalid. Using default settings.")
            return {}  # Return default settings if JSON is invalid
    return {}  # Return default settings if the file does not exist

# Save settings to JSON
def save_settings(settings):
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=4)

# Load existing settings
app_settings = load_settings()

"""----------Constants and Theme Definitions----------"""
# Set default font and theme if not set in settings
DEFAULT_FONT_FAMILY = app_settings.get("font_family", "Cambria")
DEFAULT_FONT_SIZE = app_settings.get("font_size", 14)
DEFAULT_THEME = app_settings.get("theme", "Light Theme")
DEFAULT_WINDOW_SIZE = app_settings.get("window_size", [800, 600])  # [width, height]
DEFAULT_WINDOW_POSITION = app_settings.get("window_position", [100, 100])  # [x, y]

FONT_SIZES = [str(i) for i in range(8, 98, 2)]  # Font sizes from 8 to 96 in increments of 2


# Theme definitions with background and font color
THEMES = {
    "Light Theme": {
        "style": """
            QMainWindow { background-color: white; }
            QTextEdit { background-color: white; color: black; selection-background-color: #d3d7df; }
            QMenuBar, QMenu, QToolBar { background-color: #f0f0f0; color: black; }
            QMenu::item:selected, QToolButton:hover { background-color: #e0e0e0; }
        """,
        "text_color": QColor("black"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Dark Theme": {
        "style": """
            QMainWindow { background-color: #2e2e2e; }
            QTextEdit { background-color: #1e1e1e; color: #dcdcdc; selection-background-color: #505050; }
            QMenuBar, QMenu, QToolBar { background-color: #3c3c3c; color: #dcdcdc; }
            QMenu::item:selected, QToolButton:hover { background-color: #505050; }
        """,
        "text_color": QColor("#dcdcdc"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Sepia Theme": {
        "style": """
            QMainWindow { background-color: #f5e6d2; }
            QTextEdit { background-color: #f5e6d2; color: #5b4636; selection-background-color: #d3c4b4; }
            QMenuBar, QMenu, QToolBar { background-color: #f2d7b5; color: #5b4636; }
            QMenu::item:selected, QToolButton:hover { background-color: #e6c7a0; }
        """,
        "text_color": QColor("#5b4636"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Monokai Theme": {
        "style": """
            QMainWindow { background-color: #272822; }
            QTextEdit { background-color: #272822; color: #f8f8f2; selection-background-color: #49483e; }
            QMenuBar, QMenu, QToolBar { background-color: #3e3d32; color: #f8f8f2; }
            QMenu::item:selected, QToolButton:hover { background-color: #49483e; }
        """,
        "text_color": QColor("#f8f8f2"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Ocean Blue Theme": {
        "style": """
            QMainWindow { background-color: #1a1f3b; }
            QTextEdit { background-color: #1a1f3b; color: #aaccff; selection-background-color: #3b5998; }
            QMenuBar, QMenu, QToolBar { background-color: #162447; color: #aaccff; }
            QMenu::item:selected, QToolButton:hover { background-color: #3b5998; }
        """,
        "text_color": QColor("#aaccff"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Forest Green Theme": {
        "style": """
            QMainWindow { background-color: #2b472e; }
            QTextEdit { background-color: #2b472e; color: #d3e2c2; selection-background-color: #4a6356; }
            QMenuBar, QMenu, QToolBar { background-color: #3c5c46; color: #d3e2c2; }
            QMenu::item:selected, QToolButton:hover { background-color: #4a6356; }
        """,
        "text_color": QColor("#d3e2c2"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Desert Sand Theme": {
        "style": """
            QMainWindow { background-color: #edc9af; }
            QTextEdit { background-color: #edc9af; color: #5f4632; selection-background-color: #cdb79e; }
            QMenuBar, QMenu, QToolBar { background-color: #e3b89b; color: #5f4632; }
            QMenu::item:selected, QToolButton:hover { background-color: #c7a693; }
        """,
        "text_color": QColor("#5f4632"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Lavender Theme": {
        "style": """
            QMainWindow { background-color: #e6e6fa; }
            QTextEdit { background-color: #e6e6fa; color: #4b0082; selection-background-color: #d8bfd8; }
            QMenuBar, QMenu, QToolBar { background-color: #dcdcdc; color: #4b0082; }
            QMenu::item:selected, QToolButton:hover { background-color: #c0c0c0; }
        """,
        "text_color": QColor("#4b0082"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Rose Gold Theme": {
        "style": """
            QMainWindow { background-color: #b76e79; }
            QTextEdit { background-color: #f7cac9; color: #6d1d3e; selection-background-color: #e6a6b0; }
            QMenuBar, QMenu, QToolBar { background-color: #d4a5a5; color: #6d1d3e; }
            QMenu::item:selected, QToolButton:hover { background-color: #e6a6b0; }
        """,
        "text_color": QColor("#6d1d3e"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Midnight Purple Theme": {
        "style": """
            QMainWindow { background-color: #2e1a47; }
            QTextEdit { background-color: #2e1a47; color: #d1c4e9; selection-background-color: #4a306d; }
            QMenuBar, QMenu, QToolBar { background-color: #3a245e; color: #d1c4e9; }
            QMenu::item:selected, QToolButton:hover { background-color: #4a306d; }
        """,
        "text_color": QColor("#d1c4e9"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Vintage Paper Theme": {
        "style": """
            QMainWindow { background-color: #fefbf3; }
            QTextEdit { background-color: #fefbf3; color: #3e3b32; selection-background-color: #eae0c8; }
            QMenuBar, QMenu, QToolBar { background-color: #ece3d1; color: #3e3b32; }
            QMenu::item:selected, QToolButton:hover { background-color: #e0d3c3; }
        """,
        "text_color": QColor("#3e3b32"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Cool Gray Theme": {
        "style": """
            QMainWindow { background-color: #e0e6ed; }
            QTextEdit { background-color: #d3dae0; color: #4f5b66; selection-background-color: #b0bec5; }
            QMenuBar, QMenu, QToolBar { background-color: #c5cfd6; color: #4f5b66; }
            QMenu::item:selected, QToolButton:hover { background-color: #a9b7bf; }
        """,
        "text_color": QColor("#4f5b66"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Autumn Maple Theme": {
        "style": """
            QMainWindow { background-color: #d2691e; }
            QTextEdit { background-color: #f4a460; color: #4b2e2e; selection-background-color: #e3735e; }
            QMenuBar, QMenu, QToolBar { background-color: #cc774f; color: #4b2e2e; }
            QMenu::item:selected, QToolButton:hover { background-color: #d98258; }
        """,
        "text_color": QColor("#4b2e2e"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Emerald Theme": {
        "style": """
            QMainWindow { background-color: #0a3d3e; }
            QTextEdit { background-color: #0f4d4f; color: #cde0c9; selection-background-color: #39796b; }
            QMenuBar, QMenu, QToolBar { background-color: #0f4d4f; color: #cde0c9; }
            QMenu::item:selected, QToolButton:hover { background-color: #39796b; }
        """,
        "text_color": QColor("#cde0c9"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Sunset Orange Theme": {
        "style": """
            QMainWindow { background-color: #ff6f61; }
            QTextEdit { background-color: #ff867f; color: #4d1e18; selection-background-color: #ffab91; }
            QMenuBar, QMenu, QToolBar { background-color: #ff867f; color: #4d1e18; }
            QMenu::item:selected, QToolButton:hover { background-color: #ffab91; }
        """,
        "text_color": QColor("#4d1e18"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Ice Blue Theme": {
        "style": """
            QMainWindow { background-color: #e1f5fe; }
            QTextEdit { background-color: #b3e5fc; color: #01579b; selection-background-color: #81d4fa; }
            QMenuBar, QMenu, QToolBar { background-color: #b3e5fc; color: #01579b; }
            QMenu::item:selected, QToolButton:hover { background-color: #81d4fa; }
        """,
        "text_color": QColor("#01579b"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Bronze Theme": {
        "style": """
            QMainWindow { background-color: #cd7f32; }
            QTextEdit { background-color: #d89b5e; color: #3b1e06; selection-background-color: #b87333; }
            QMenuBar, QMenu, QToolBar { background-color: #b87333; color: #3b1e06; }
            QMenu::item:selected, QToolButton:hover { background-color: #d89b5e; }
        """,
        "text_color": QColor("#3b1e06"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Berry Purple Theme": {
        "style": """
            QMainWindow { background-color: #4b0082; }
            QTextEdit { background-color: #6a0dad; color: #e6e6fa; selection-background-color: #9932cc; }
            QMenuBar, QMenu, QToolBar { background-color: #6a0dad; color: #e6e6fa; }
            QMenu::item:selected, QToolButton:hover { background-color: #9932cc; }
        """,
        "text_color": QColor("#e6e6fa"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Aqua Marine Theme": {
        "style": """
            QMainWindow { background-color: #7fdbff; }
            QTextEdit { background-color: #0074d9; color: #001f3f; selection-background-color: #39c0ed; }
            QMenuBar, QMenu, QToolBar { background-color: #0074d9; color: #ffffff; }
            QMenu::item:selected, QToolButton:hover { background-color: #39c0ed; }
        """,
        "text_color": QColor("#001f3f"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Rustic Red Theme": {
        "style": """
            QMainWindow { background-color: #8b0000; }
            QTextEdit { background-color: #b22222; color: #f5f5f5; selection-background-color: #cd5c5c; }
            QMenuBar, QMenu, QToolBar { background-color: #a52a2a; color: #f5f5f5; }
            QMenu::item:selected, QToolButton:hover { background-color: #cd5c5c; }
        """,
        "text_color": QColor("#f5f5f5"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Peach Blossom Theme": {
        "style": """
            QMainWindow { background-color: #ffe5b4; }
            QTextEdit { background-color: #ffdab9; color: #8b4513; selection-background-color: #ffdead; }
            QMenuBar, QMenu, QToolBar { background-color: #ffdead; color: #8b4513; }
            QMenu::item:selected, QToolButton:hover { background-color: #ffe4c4; }
        """,
        "text_color": QColor("#8b4513"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Deep Space Theme": {
        "style": """
            QMainWindow { background-color: #0d0d0d; }
            QTextEdit { background-color: #1a1a1a; color: #b0b0b0; selection-background-color: #333333; }
            QMenuBar, QMenu, QToolBar { background-color: #1a1a1a; color: #b0b0b0; }
            QMenu::item:selected, QToolButton:hover { background-color: #333333; }
        """,
        "text_color": QColor("#b0b0b0"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Olive Green Theme": {
        "style": """
            QMainWindow { background-color: #556b2f; }
            QTextEdit { background-color: #6b8e23; color: #f0e68c; selection-background-color: #bdb76b; }
            QMenuBar, QMenu, QToolBar { background-color: #808000; color: #f0e68c; }
            QMenu::item:selected, QToolButton:hover { background-color: #bdb76b; }
        """,
        "text_color": QColor("#f0e68c"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Amber Glow Theme": {
        "style": """
            QMainWindow { background-color: #ffbf00; }
            QTextEdit { background-color: #ffdd44; color: #4a3c00; selection-background-color: #ffe680; }
            QMenuBar, QMenu, QToolBar { background-color: #ffdd44; color: #4a3c00; }
            QMenu::item:selected, QToolButton:hover { background-color: #ffe680; }
        """,
        "text_color": QColor("#4a3c00"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    },
    "Golden Yellow Theme": {
        "style": """
            QMainWindow { background-color: #ffd700; }
            QTextEdit { background-color: #ffec8b; color: #6b4226; selection-background-color: #ffd662; }
            QMenuBar, QMenu, QToolBar { background-color: #ffec8b; color: #6b4226; }
            QMenu::item:selected, QToolButton:hover { background-color: #ffd662; }
        """,
        "text_color": QColor("#6b4226"),
        "font_family": DEFAULT_FONT_FAMILY,
        "font_size": DEFAULT_FONT_SIZE
    }
}

# Highlight styles
HIGHLIGHT_STYLES = {
    "Light Yellow / Dark Gray": {"highlight": QColor(255, 255, 204), "font": QColor(64, 64, 64)},
    "Light Blue / Dark Navy": {"highlight": QColor(204, 229, 255), "font": QColor(0, 0, 51)},
    "Light Green / Dark Green": {"highlight": QColor(204, 255, 204), "font": QColor(0, 51, 0)},
    "Light Pink / Dark Purple": {"highlight": QColor(255, 204, 229), "font": QColor(51, 0, 51)},
    "Light Orange / Dark Brown": {"highlight": QColor(255, 229, 204), "font": QColor(102, 51, 0)},
    "Light Gray / Black": {"highlight": QColor(224, 224, 224), "font": QColor(0, 0, 0)},
    "Light Purple / Dark Purple": {"highlight": QColor(229, 204, 255), "font": QColor(51, 0, 51)}
}

# Define a style for toggled (active) buttons
TOGGLED_BUTTON_STYLE = """
    QToolButton:checked {
        background-color: #4CAF50;  /* Change to a green color or your preferred active color */
        border: 2px solid #3E8E41;  /* Optional: Darker border */
        color: white;  /* Change text color for better visibility */
    }
"""

"""===========Snipping Overlay Class=========="""
class SnippingOverlay(QWidget):
    snipCompleteGlobal = pyqtSignal(QRect)

    def __init__(self, screen_rect, close_all_callback):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(screen_rect)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.begin = QPoint()
        self.end = QPoint()
        self.close_all_callback = close_all_callback

    def updateMask(self):
        # Create a mask with the entire area filled
        mask = QBitmap(self.size())
        mask.fill(Qt.GlobalColor.black)
        
        # Define the selection rectangle
        selection_rect = QRect(self.begin, self.end).normalized()

        # Use QPainter to clear the selected area in the mask
        painter = QPainter(mask)
        painter.setBrush(Qt.GlobalColor.white)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(selection_rect)
        painter.end()

        # Apply the mask to make the selection area transparent
        self.setMask(mask)

    def paintEvent(self, event):
        qp = QPainter(self)
        screen_rect = self.rect()

        # Draw a semi-transparent overlay over the entire screen
        qp.setBrush(QColor(0, 0, 0, 100))  # Semi-transparent dark overlay
        qp.setPen(Qt.PenStyle.NoPen)
        qp.drawRect(screen_rect)

        # Draw a clear border around the selection rectangle
        selection_rect = QRect(self.begin, self.end).normalized()
        if not selection_rect.isNull():
            qp.setPen(QPen(Qt.GlobalColor.red, 3))  # Red outline for selection
            qp.drawRect(selection_rect)

    def mousePressEvent(self, event):
        self.begin = event.pos()
        self.end = self.begin
        self.updateMask()
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.updateMask()
        self.update()

    def mouseReleaseEvent(self, event):
        self.end = event.pos()
        self.updateMask()
        self.update()
        # Adjust the coordinates to global
        snip_rect = QRect(self.mapToGlobal(self.begin), self.mapToGlobal(self.end)).normalized()
        self.snipCompleteGlobal.emit(snip_rect)
        self.close_all_callback(snip_rect)
        self.close()

"""===========Main Application Class=========="""
# Initialization and UI Setup
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Case and Note Organizer 2.0")
        
        # Flag to track if capture area has been set
        self.capture_area_set = False

        # Ensure current highlight color is set before initializing UI
        self.current_highlight_color = list(HIGHLIGHT_STYLES.values())[0]  # Default to the first color

        self.images_dir = os.path.join(os.path.dirname(__file__), 'images')  # Path to icons

        # Load settings for font and theme
        self.current_theme = app_settings.get("theme", DEFAULT_THEME)
        self.current_theme_settings = THEMES.get(self.current_theme, THEMES["Light Theme"])
        self.current_font_family = app_settings.get("font_family", DEFAULT_FONT_FAMILY)
        self.current_font_size = app_settings.get("font_size", DEFAULT_FONT_SIZE)
        
                # Set window size and position from settings
        window_size = app_settings.get("window_size", DEFAULT_WINDOW_SIZE)
        window_position = app_settings.get("window_position", DEFAULT_WINDOW_POSITION)
        self.resize(window_size[0], window_size[1])
        self.move(window_position[0], window_position[1])
        
        # Initialize path tracking
        self.paths = {}  # Stores file paths for each tab

        # Set up main tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self.show_tab_context_menu)
        self.setCentralWidget(self.tab_widget)

        # Add the initial tab
        self.add_new_tab()
        
        # Set up the context menu
        self.setup_custom_context_menu()
        
        # Initialize UI components
        self.apply_default_font_settings()
        self.init_ui()

      
        # Apply global style for toggled buttons
        self.setStyleSheet(TOGGLED_BUTTON_STYLE)    
        
        # Apply the loaded theme
        self.apply_theme(self.current_theme)

        logger.info("User interface initialized with tab support.")

    def init_ui(self):
        """Initialize menus, toolbars, and theme settings."""
        menubar = self.menuBar()
        self.file_menu = menubar.addMenu("File")
        self.edit_menu = menubar.addMenu("Edit")
        self.format_menu = menubar.addMenu("Format")
        self.font_menu = menubar.addMenu("Font")
        self.settings_menu = menubar.addMenu("Settings")

        # Add Themes menu under Settings
        self.themes_menu = QMenu("Themes", self)
        self.settings_menu.addMenu(self.themes_menu)
        for theme_name in THEMES.keys():
            theme_action = QAction(theme_name, self)
            theme_action.triggered.connect(lambda checked, name=theme_name: self.apply_theme(name))
            self.themes_menu.addAction(theme_action)

        # Initialize toolbars in the correct order
        self.init_file_toolbar()
        self.init_edit_toolbar()
        self.init_font_toolbar()
        self.init_format_toolbar()  # Initialize format toolbar here
        self.init_spell_check_toolbar()  # Spell check toolbar uses format toolbar
        self.init_align_toolbar()
        self.init_list_toolbar()
        self.init_capture_toolbar()
        
    """----------Tab Management Methods----------"""
    def add_new_tab(self, checked=False, text=""):
        # Ensure 'text' is a string
        if not isinstance(text, str):
            text = ""

        new_tab = QTextEdit()
        new_tab.setFont(QFont(self.current_font_family, self.current_font_size))
        new_tab.setPlainText(text)
        new_tab.installEventFilter(self)
        
        # Ensure custom context menu is set up
        self.setup_custom_context_menu()
        
        index = self.tab_widget.addTab(new_tab, "Untitled")
        self.paths[index] = None
        self.tab_widget.setCurrentIndex(index)

    def close_tab(self, index):
        editor = self.tab_widget.widget(index)
        if editor is not None and editor.document().isModified():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "This tab has unsaved changes. Do you want to save before closing?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save:
                self.file_save(index)
            elif reply == QMessageBox.StandardButton.Cancel:
                return  # Cancel close

        # Remove the tab
        self.tab_widget.removeTab(index)
        self.paths.pop(index, None)

    def show_tab_context_menu(self, position):
        tab_index = self.tab_widget.tabBar().tabAt(position)
        if tab_index >= 0:
            menu = QMenu()
            rename_action = QAction('Rename Tab', self)
            rename_action.triggered.connect(lambda: self.rename_tab(tab_index))
            menu.addAction(rename_action)
            menu.exec(self.tab_widget.tabBar().mapToGlobal(position))

    def rename_tab(self, index):
        current_title = self.tab_widget.tabText(index)
        text, ok = QInputDialog.getText(self, 'Rename Tab', 'Enter new tab name:', text=current_title)
        if ok and text:
            self.tab_widget.setTabText(index, text)
            self.tab_widget.setTabToolTip(index, text)
            
    """----------Editor Access Methods----------"""
    def get_current_editor(self):
        return self.tab_widget.currentWidget()

    def get_current_tab_index(self):
        return self.tab_widget.currentIndex()
        
    """----------File Toolbar----------"""
    def init_file_toolbar(self):
        toolbar = QToolBar("File")
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        # New Tab
        new_tab_action = QAction(QIcon(os.path.join(self.images_dir, 'new_file.png')), "New Tab", self)
        new_tab_action.setShortcut("Ctrl+T")
        new_tab_action.triggered.connect(self.add_new_tab)
        toolbar.addAction(new_tab_action)
        self.file_menu.addAction(new_tab_action)
        
        # Open File
        open_action = QAction(QIcon(os.path.join(self.images_dir, 'open_file.png')), "Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.file_open)
        toolbar.addAction(open_action)
        self.file_menu.addAction(open_action)
        
        # Save File
        save_action = QAction(QIcon(os.path.join(self.images_dir, 'save.png')), "Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(lambda: self.file_save(self.tab_widget.currentIndex()))
        toolbar.addAction(save_action)
        self.file_menu.addAction(save_action)

        # Save As
        saveas_action = QAction(QIcon(os.path.join(self.images_dir, 'save_as.png')), "Save As...", self)
        saveas_action.setShortcut("Ctrl+Alt+S")
        saveas_action.triggered.connect(lambda: self.file_saveas(self.tab_widget.currentIndex()))
        toolbar.addAction(saveas_action)
        self.file_menu.addAction(saveas_action)

    """----------Edit Toolbar----------"""
    def init_edit_toolbar(self):
        edit_toolbar = QToolBar("Edit")
        edit_toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(edit_toolbar)

        undo_action = QAction(QIcon(os.path.join(self.images_dir, 'arrow-curve_left.png')), "Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(lambda: self.get_current_editor().undo())
        edit_toolbar.addAction(undo_action)
        self.edit_menu.addAction(undo_action)

        redo_action = QAction(QIcon(os.path.join(self.images_dir, 'arrow-curve_right.png')), "Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(lambda: self.get_current_editor().redo())
        edit_toolbar.addAction(redo_action)
        self.edit_menu.addAction(redo_action)

        cut_action = QAction(QIcon(os.path.join(self.images_dir, 'scissors.png')), "Cut", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(lambda: self.get_current_editor().cut())
        edit_toolbar.addAction(cut_action)
        self.edit_menu.addAction(cut_action)

        copy_action = QAction(QIcon(os.path.join(self.images_dir, 'document-copy.png')), "Copy", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(lambda: self.get_current_editor().copy())
        edit_toolbar.addAction(copy_action)
        self.edit_menu.addAction(copy_action)

        paste_action = QAction(QIcon(os.path.join(self.images_dir, 'clipboard-paste-document-text.png')), "Paste", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(lambda: self.get_current_editor().paste())
        edit_toolbar.addAction(paste_action)
        self.edit_menu.addAction(paste_action)

    """----------Font Toolbar----------"""
    def init_font_toolbar(self):
        toolbar = QToolBar("Font")
        toolbar.setIconSize(QSize(10, 10))
        self.addToolBar(toolbar)

        # Font ComboBox
        font_box = QFontComboBox()
        font_box.setCurrentFont(QFont(self.current_font_family))
        font_box.currentFontChanged.connect(self.on_font_change)
        toolbar.addWidget(font_box)

        # Font Size ComboBox
        size_box = QComboBox()
        size_box.addItems(FONT_SIZES)
        size_box.setCurrentText(str(self.current_font_size))
        size_box.currentTextChanged.connect(self.on_fontsize_change)
        size_box.setMinimumWidth(50)
        toolbar.addWidget(size_box)

        # Clear Formatting Button
        clear_format_action = QAction(QIcon(os.path.join(self.images_dir, 'clear_format.png')), "Clear Formatting", self)
        clear_format_action.setShortcut("Ctrl+Space")
        clear_format_action.triggered.connect(self.clear_formatting)
        toolbar.addAction(clear_format_action)
        
    """----------Spell Check Toolbar-----------"""
    def init_spell_check_toolbar(self):
        # Initialize spell check action with toggle behavior
        spell_check_action = QAction(QIcon(os.path.join(self.images_dir, 'spellcheck.png')), "Spell Check", self)
        spell_check_action.setCheckable(True)
        spell_check_action.toggled.connect(self.toggle_real_time_spell_check)  # Connect toggling
        self.format_toolbar.addAction(spell_check_action)
        self.spell_check_action = spell_check_action  # Store action reference

    """----------Format Toolbar----------"""
    def init_format_toolbar(self):
        """Initialize the format toolbar and assign it to self.format_toolbar."""
        self.format_toolbar = QToolBar("Format")
        self.format_toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(self.format_toolbar)

        # Bold Button
        self.bold_action = QAction(QIcon(os.path.join(self.images_dir, 'bold.png')), "Bold", self)
        self.bold_action.setCheckable(True)
        self.bold_action.setShortcut("Ctrl+B")
        self.bold_action.toggled.connect(lambda checked: self.toggle_text_format("bold", checked))
        self.format_toolbar.addAction(self.bold_action)

        # Italic Button
        self.italic_action = QAction(QIcon(os.path.join(self.images_dir, 'italic.png')), "Italic", self)
        self.italic_action.setCheckable(True)
        self.italic_action.setShortcut("Ctrl+I")
        self.italic_action.toggled.connect(lambda checked: self.toggle_text_format("italic", checked))
        self.format_toolbar.addAction(self.italic_action)

        # Underline Button
        self.underline_action = QAction(QIcon(os.path.join(self.images_dir, 'underline.png')), "Underline", self)
        self.underline_action.setCheckable(True)
        self.underline_action.setShortcut("Ctrl+U")
        self.underline_action.toggled.connect(lambda checked: self.toggle_text_format("underline", checked))
        self.format_toolbar.addAction(self.underline_action)

        # Strikethrough Button
        self.strikethrough_action = QAction(QIcon(os.path.join(self.images_dir, 'strikethrough.png')), "Strikethrough", self)
        self.strikethrough_action.setCheckable(True)
        self.strikethrough_action.toggled.connect(lambda checked: self.toggle_text_format("strikethrough", checked))
        self.format_toolbar.addAction(self.strikethrough_action)

        # Highlight Button with Dropdown
        self.highlight_action = QAction(QIcon(os.path.join(self.images_dir, 'highlighter.png')), "Highlight", self)
        self.highlight_action.setCheckable(True)
        self.highlight_action.toggled.connect(lambda checked: self.toggle_highlighting(checked))
        self.format_toolbar.addAction(self.highlight_action)

        # Create a dropdown menu for highlight color selection
        highlight_menu = QMenu("Highlight Colors", self)
        highlight_group = QActionGroup(self)  # Make actions exclusive in the menu
        highlight_group.setExclusive(True)

        for name, colors in HIGHLIGHT_STYLES.items():
            action = self.create_highlight_action(name, colors)
            action.setCheckable(True)
            action.setData(colors)
            action.triggered.connect(self.on_highlight_color_selected)
            highlight_group.addAction(action)
            highlight_menu.addAction(action)

        # Attach menu to highlight action
        self.highlight_action.setMenu(highlight_menu)
        self.current_highlight_color = list(HIGHLIGHT_STYLES.values())[0]  # Default color

        # Clear Formatting Button
        clear_format_action = QAction(QIcon(os.path.join(self.images_dir, 'clear_format.png')), "Clear Formatting", self)
        clear_format_action.setShortcut("Ctrl+Space")
        clear_format_action.triggered.connect(self.clear_formatting)
        self.format_toolbar.addAction(clear_format_action)

    """----------Alignment Toolbar----------"""
    def init_align_toolbar(self):
        align_toolbar = QToolBar("Align")
        self.addToolBar(align_toolbar)

        align_actions = [
            ("<- Align Left", "align-left.png", Qt.AlignmentFlag.AlignLeft),
            ("Align Center", "align-center.png", Qt.AlignmentFlag.AlignCenter),
            ("Align Right ->", "align-right.png", Qt.AlignmentFlag.AlignRight),
            ("<--> Justify", "align-justify.png", Qt.AlignmentFlag.AlignJustify)
        ]
        for name, icon, alignment in align_actions:
            action = QAction(QIcon(os.path.join(self.images_dir, icon)), name, self)
            action.setCheckable(True)
            action.triggered.connect(lambda _, a=alignment: self.get_current_editor().setAlignment(a))
            align_toolbar.addAction(action)
            self.format_menu.addAction(action)

    """----------List Toolbar----------"""
    def init_list_toolbar(self):
        list_toolbar = QToolBar("Lists")
        list_toolbar.setIconSize(QSize(25, 25))
        self.addToolBar(list_toolbar)

        bullet_list_action = QAction(QIcon(os.path.join(self.images_dir, 'bullet.png')), "Bullet List", self)
        bullet_list_action.setShortcut("Ctrl+Shift+L")
        bullet_list_action.triggered.connect(self.add_bullet_list)
        list_toolbar.addAction(bullet_list_action)
        self.format_menu.addAction(bullet_list_action)

        numbered_list_action = QAction(QIcon(os.path.join(self.images_dir, 'numbered-list.png')), "Numbered List", self)
        numbered_list_action.setShortcut("Ctrl+Shift+N")
        numbered_list_action.triggered.connect(self.add_numbered_list)
        list_toolbar.addAction(numbered_list_action)
        self.format_menu.addAction(numbered_list_action)

        increase_indent_action = QAction(QIcon(os.path.join(self.images_dir, 'indent.png')), "Increase Indent", self)
        increase_indent_action.setShortcut("Ctrl+Tab")
        increase_indent_action.triggered.connect(self.increase_indent)
        list_toolbar.addAction(increase_indent_action)

        decrease_indent_action = QAction(QIcon(os.path.join(self.images_dir, 'outdent.png')), "Decrease Indent", self)
        decrease_indent_action.setShortcut("Ctrl+Shift+Tab")
        decrease_indent_action.triggered.connect(self.decrease_indent)
        list_toolbar.addAction(decrease_indent_action)
        
    """----------Capture Toolbar----------"""  
    def init_capture_toolbar(self):
        """Initialize Capture toolbar."""
        self.capture_toolbar = QToolBar("Capture")
        self.capture_toolbar.setIconSize(QSize(25, 25))  # Set the icon size for this toolbar
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.capture_toolbar)

        # Set Capture Area Button
        set_capture_area_action = QAction(QIcon(os.path.join(self.images_dir, 'set_capture.png')), "Set Capture Area", self)
        set_capture_area_action.triggered.connect(self.set_capture_area)
        self.capture_toolbar.addAction(set_capture_area_action)
        
        # Spacer Widget
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.capture_toolbar.addWidget(spacer)  # Adds the spacer between buttons        
        
        # OCR Button
        ocr_button = QPushButton(QIcon(os.path.join(self.images_dir, 'ocr.png')), "", self)
        ocr_button.setIconSize(QSize(45, 45))  
        ocr_button.clicked.connect(self.perform_ocr)
        self.capture_toolbar.addWidget(ocr_button)  
    
        # Capture Button with larger icon
        capture_button = QPushButton(QIcon(os.path.join(self.images_dir, 'capture.png')), "", self)
        capture_button.setIconSize(QSize(45, 45))
        capture_button.clicked.connect(self.capture)
        self.capture_toolbar.addWidget(capture_button)

    """----------Formatting and Theme Methods----------"""
    def get_combined_stylesheet(self, theme_style):
        return theme_style + TOGGLED_BUTTON_STYLE

    # Adjust apply_theme to use the combined stylesheet
    def apply_theme(self, theme_name):
        theme = THEMES.get(theme_name, THEMES["Light Theme"])
        self.current_theme = theme_name
        
        # Combine the theme style with the toggled button style
        combined_style = self.get_combined_stylesheet(theme["style"])
        self.setStyleSheet(combined_style)
        
        # Update other theme-specific settings
        self.current_theme_settings.update({
            "text_color": theme["text_color"],
            "font_family": theme["font_family"],
            "font_size": theme["font_size"]
        })
        self.apply_default_font_settings()
        logger.info(f"Theme applied: {theme_name}")

    # Apply default font settings to current editor
    def apply_default_font_settings(self):
        editor = self.get_current_editor()
        if editor:
            editor.setFont(QFont(self.current_theme_settings["font_family"], self.current_theme_settings["font_size"]))

    # Font Change Handlers
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
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            format = QTextCharFormat()
            format.setFontFamily(self.current_font_family)
            format.setFontPointSize(self.current_font_size)
            if cursor.hasSelection():
                cursor.setCharFormat(format)
            else:
                editor.setCurrentFont(QFont(self.current_font_family, self.current_font_size))
                cursor.mergeCharFormat(format)

    """----------Text Formatting Methods----------"""
    def toggle_text_format(self, format_type, checked):
        """Toggle text formatting (bold, italic, underline, strikethrough) based on the checked state."""
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            format = QTextCharFormat()

            if format_type == "bold":
                format.setFontWeight(QFont.Weight.Bold if checked else QFont.Weight.Normal)
            elif format_type == "italic":
                format.setFontItalic(checked)
            elif format_type == "underline":
                format.setFontUnderline(checked)
            elif format_type == "strikethrough":
                format.setFontStrikeOut(checked)

            cursor.mergeCharFormat(format)
            editor.setTextCursor(cursor)

    def toggle_bold(self, checked):
        format = QTextCharFormat()
        format.setFontWeight(QFont.Weight.Bold if checked else QFont.Weight.Normal)
        self.apply_format_to_selection_or_cursor(format)

    def toggle_italic(self, checked):
        format = QTextCharFormat()
        format.setFontItalic(checked)
        self.apply_format_to_selection_or_cursor(format)

    def toggle_underline(self, checked):
        format = QTextCharFormat()
        format.setFontUnderline(checked)
        self.apply_format_to_selection_or_cursor(format)

    def toggle_strikethrough(self, checked):
        format = QTextCharFormat()
        format.setFontStrikeOut(checked)
        self.apply_format_to_selection_or_cursor(format)

    def merge_format(self, format):
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            if cursor.hasSelection():
                cursor.mergeCharFormat(format)
            else:
                editor.mergeCurrentCharFormat(format)

    """----------Highlighting Methods----------"""
    def open_highlight_menu(self):
        editor = self.get_current_editor()
        if editor:
            highlight_menu = QMenu("Highlight Styles", self)
            for name, colors in HIGHLIGHT_STYLES.items():
                action = self.create_highlight_action(name, colors)
                highlight_menu.addAction(action)

            cursor_position = editor.cursorRect().bottomRight()
            highlight_menu.popup(editor.mapToGlobal(cursor_position))

    def create_highlight_action(self, name, colors):
        """Create an action with a color preview label for the dropdown."""
        action = QWidgetAction(self)
        label = QLabel(name)
        label.setFont(QFont(DEFAULT_FONT_FAMILY, 12))
        label.setStyleSheet(
            f"background-color: rgb({colors['highlight'].red()}, {colors['highlight'].green()}, {colors['highlight'].blue()}); "
            f"color: rgb({colors['font'].red()}, {colors['font'].green()}, {colors['font'].blue()}); "
            "padding: 5px; margin: 1px;"
        )
        action.setDefaultWidget(label)
        return action

    def toggle_highlighting(self, checked):
        """Toggle highlighting on/off with current highlight color if checked."""
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            format = cursor.charFormat()

            if checked:
                format.setBackground(self.current_highlight_color["highlight"])
                format.setForeground(self.current_highlight_color["font"])
            else:
                format.setBackground(Qt.GlobalColor.transparent)
                format.setForeground(self.current_theme_settings["text_color"])

            cursor.mergeCharFormat(format)
            editor.setTextCursor(cursor)

    def set_highlight_color(self, color):
        """Set the selected highlight color and update current_highlight_color correctly."""
        if isinstance(color, dict):
            self.current_highlight_color = color  # Ensure it's always a dictionary
        else:
            self.current_highlight_color = HIGHLIGHT_STYLES.get(color, list(HIGHLIGHT_STYLES.values())[0]) # Fallback if needed
        if self.highlight_action.isChecked():
            # If highlight toggle is on, apply the new color immediately
            self.apply_highlight_style(self.current_highlight_color)

    def on_highlight_color_selected(self):
        """Update the current highlight color and apply it immediately if the highlighter is active."""
        action = self.sender()
        color = action.data()  # Retrieve stored color data from QAction
        self.current_highlight_color = color  # Update the active color
        if self.highlight_action.isChecked():
            self.apply_highlight_style(color)  # Apply the selected color immediately

    def apply_highlight_style(self, color):
        """Apply the selected highlight color to the current text cursor or selection,
           merging with existing formatting like bold, italic, underline, and strikethrough."""
        editor = self.get_current_editor()
        if editor and isinstance(color, dict):  # Ensure color is a valid dictionary
            cursor = editor.textCursor()
            format = cursor.charFormat()

            # Update background and foreground for highlight
            format.setBackground(color["highlight"])
            format.setForeground(color["font"])

            # Merge the updated format with the current selection
            if cursor.hasSelection():
                cursor.setCharFormat(format)
            else:
                cursor.mergeCharFormat(format)

            editor.setTextCursor(cursor)  # Ensure cursor updates after applying format
            editor.setFocus()  # Return focus to editor

    """----------Clear Formatting Method----------"""
    def clear_formatting(self):
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            format = QTextCharFormat()
            format.setFont(QFont(self.current_theme_settings["font_family"], self.current_theme_settings["font_size"]))
            format.setForeground(self.current_theme_settings["text_color"])
            format.setBackground(Qt.GlobalColor.transparent)
            
            # Apply formatting to selection if there's a selection, or to the cursor if there's no selection
            if cursor.hasSelection():
                cursor.mergeCharFormat(format)
            else:
                editor.setCurrentFont(QFont(self.current_theme_settings["font_family"], self.current_theme_settings["font_size"]))
                editor.mergeCurrentCharFormat(format)
            
            logger.info("Cleared formatting to current theme defaults.")
            
    """----------Spell Check Methods-----------"""
    def setup_custom_context_menu(self):
        """Sets up the custom context menu for the current editor in the active tab."""
        editor = self.get_current_editor()
        if editor:
            # Set the custom context menu policy and connect to the custom menu slot
            editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            editor.customContextMenuRequested.connect(self.show_custom_context_menu)

    def show_custom_context_menu(self, pos):
        """Display a custom context menu with spell check suggestions."""
        editor = self.get_current_editor()
        if editor:
            menu = QMenu(self)  # Start with a fresh custom menu

            # Check if the cursor is on a misspelled word
            cursor = editor.cursorForPosition(pos)
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            word = cursor.selectedText()

            if word and word not in spell:
                # Create a spell-check submenu for suggestions
                spell_check_menu = QMenu("Spell Check", menu)
                self.populate_spell_check_menu(word, cursor, spell_check_menu)
                menu.addMenu(spell_check_menu)
            
            # Add standard actions like Cut, Copy, Paste, etc.
            menu.addSeparator()
            menu.addAction("Cut", editor.cut)
            menu.addAction("Copy", editor.copy)
            menu.addAction("Paste", editor.paste)
            menu.addAction("Select All", editor.selectAll)

            # Show the custom menu at the specified position
            menu.exec(editor.mapToGlobal(pos))

    def populate_spell_check_menu(self, word, cursor, spell_check_menu):
        """Populates the spell check submenu with suggestions and add-to-dictionary options."""
        suggestions = spell.candidates(word)
        for suggestion in suggestions:
            action = QAction(suggestion, self)
            action.triggered.connect(lambda _, sug=suggestion: self.replace_word(cursor, sug))
            spell_check_menu.addAction(action)
        
        # Add an option to add the word to the custom dictionary
        add_to_dict_action = QAction("Add to Dictionary", self)
        add_to_dict_action.triggered.connect(lambda _, w=word: self.add_word_to_dictionary(w))
        spell_check_menu.addAction(add_to_dict_action)        
    
    # Spell Check Timer and Real-Time Spell Check Toggle
    def toggle_real_time_spell_check(self, checked):
        editor = self.get_current_editor()
        if checked:
            # Activate real-time spell check
            self.spell_check_timer = QTimer()
            self.spell_check_timer.setSingleShot(True)
            self.spell_check_timer.timeout.connect(self.perform_real_time_spell_check)
            if editor:
                editor.textChanged.connect(lambda: self.spell_check_timer.start(500))
            logger.info("Real-time spell check enabled.")
        else:
            # Deactivate real-time spell check
            if editor:
                try:
                    editor.textChanged.disconnect()
                except TypeError:
                    pass  # If already disconnected
            logger.info("Real-time spell check disabled.")         
 
    def setup_custom_context_menu(self):
        """Sets up a custom context menu for the text editor, adding spell check options."""
        editor = self.get_current_editor()
        if editor:
            # Set the custom context menu policy and connect the custom menu slot
            editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            editor.customContextMenuRequested.connect(self.show_custom_context_menu)

    def show_custom_context_menu(self, pos):
        """Display a custom context menu with spell check suggestions if a misspelled word is detected."""
        editor = self.get_current_editor()
        if editor:
            # Custom context menu setup without default items
            menu = QMenu(self)

            # Detect and select the word under cursor for spell checking
            cursor = editor.cursorForPosition(pos)
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            word = cursor.selectedText()

            if word and word not in spell:
                # Create spell-check submenu if the word is misspelled
                spell_check_menu = QMenu("Spell Check", menu)
                self.populate_spell_check_menu(word, cursor, spell_check_menu)
                menu.addMenu(spell_check_menu)

            # Add standard text edit options
            menu.addSeparator()
            menu.addAction("Cut", editor.cut)
            menu.addAction("Copy", editor.copy)
            menu.addAction("Paste", editor.paste)
            menu.addAction("Select All", editor.selectAll)

            # Show custom menu at the specified position
            menu.exec(editor.mapToGlobal(pos))

    def populate_spell_check_menu(self, word, cursor, spell_check_menu):
        """Adds spell check suggestions and dictionary options to the custom menu."""
        suggestions = spell.candidates(word)
        for suggestion in suggestions:
            action = QAction(suggestion, self)
            action.triggered.connect(lambda _, sug=suggestion: self.replace_word(cursor, sug))
            spell_check_menu.addAction(action)
        
        # Add "Add to Dictionary" option for custom dictionary
        add_to_dict_action = QAction("Add to Dictionary", self)
        add_to_dict_action.triggered.connect(lambda _, w=word: self.add_word_to_dictionary(w))
        spell_check_menu.addAction(add_to_dict_action)

    def show_spell_check_context_menu(self, misspelled_words, cursor, menu):
        """Adds spell check suggestions to the context menu."""
        for word in misspelled_words:
            suggestions = spell.candidates(word)
            
            # Add each suggestion to the menu
            for suggestion in suggestions:
                action = QAction(suggestion, self)
                action.triggered.connect(lambda _, sug=suggestion: self.replace_word(cursor, sug))
                menu.addAction(action)

            # Option to add the word to the custom dictionary
            add_word_action = QAction("Add to Dictionary", self)
            add_word_action.triggered.connect(lambda _, w=word: self.add_word_to_dictionary(w))
            menu.addAction(add_word_action)
 
        # Manual Spell Check for Selected Text
        def perform_spell_check(self):
            editor = self.get_current_editor()
            if editor:
                cursor = editor.textCursor()
                text = cursor.selectedText() or editor.toPlainText()  # Check selected text or whole document
                misspelled = spell.unknown(text.split())
                
                if misspelled:
                    self.show_spell_check_context_menu(misspelled, cursor)
                    
    def perform_real_time_spell_check(self):
        """Underline misspelled words in real time."""
        editor = self.get_current_editor()
        if editor:
            # Remove previous spell-check underlines
            cursor = editor.textCursor()
            cursor.select(QTextCursor.SelectionType.Document)
            cursor.setCharFormat(QTextCharFormat())  # Clear all formatting

            # Iterate through each word in the document
            text = editor.toPlainText()
            words = text.split()
            position = 0
            for word in words:
                # Check if word is misspelled
                if word not in spell:
                    # Highlight misspelled word with an underline
                    cursor.setPosition(position)
                    cursor.movePosition(QTextCursor.MoveOperation.NextWord, QTextCursor.MoveMode.KeepAnchor)
                    format = QTextCharFormat()
                    format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
                    format.setUnderlineColor(Qt.GlobalColor.red)
                    cursor.mergeCharFormat(format)
                position += len(word) + 1  # Move position after each word                    

    def replace_word(self, cursor, replacement):
        """Replaces the misspelled word with the selected suggestion."""
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(replacement)
        cursor.endEditBlock()

    def add_word_to_dictionary(self, word):
        """Adds a word to the custom dictionary and saves persistently."""
        spell.word_frequency.add(word)
        self.save_custom_dictionary()
        QMessageBox.information(self, "Word Added", f"'{word}' has been added to the dictionary.")
        logger.info(f"Added '{word}' to custom dictionary.")

    def save_custom_dictionary(self):
        """Save the custom dictionary to the JSON file for persistence."""
        with open(custom_dict_path, 'w') as f:
            json.dump(list(spell.word_frequency.dictionary.keys()), f, indent=4)     
            
    """----------List Methods----------"""
    # List and Indentation Methods
    def add_bullet_list(self):
        """Applies a bullet list format to the selected text or the current line."""
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.beginEditBlock()

            # Check if the current cursor position is in a list; if so, remove it.
            current_list = cursor.currentList()
            if current_list and current_list.format().style() == QTextListFormat.Style.ListDisc:
                block_format = cursor.blockFormat()
                block_format.setIndent(0)
                cursor.setBlockFormat(block_format)
            else:
                # Apply bullet list format
                list_format = QTextListFormat()
                list_format.setStyle(QTextListFormat.Style.ListDisc)
                cursor.createList(list_format)

            cursor.endEditBlock()
            logging.info("Bullet list applied.")

    def add_numbered_list(self):
        """Applies a numbered list format to the selected text or the current line."""
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.beginEditBlock()

            # Check if the current cursor position is in a list; if so, remove it.
            current_list = cursor.currentList()
            if current_list and current_list.format().style() == QTextListFormat.Style.ListDecimal:
                block_format = cursor.blockFormat()
                block_format.setIndent(0)
                cursor.setBlockFormat(block_format)
            else:
                # Apply numbered list format
                list_format = QTextListFormat()
                list_format.setStyle(QTextListFormat.Style.ListDecimal)
                cursor.createList(list_format)

            cursor.endEditBlock()
            logging.info("Numbered list applied.")
            
    def increase_indent(self):
        """Increases the indent level of the current line or selected text."""
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.beginEditBlock()

            # Get the current block format and increase its indent level by 1
            block_format = cursor.blockFormat()
            block_format.setIndent(block_format.indent() + 1)
            cursor.setBlockFormat(block_format)

            cursor.endEditBlock()
            logging.info("Increased indent level.")

    def decrease_indent(self):
        """Decreases the indent level of the current line or selected text."""
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.beginEditBlock()

            # Get the current block format and decrease its indent level by 1, to a minimum of 0
            block_format = cursor.blockFormat()
            block_format.setIndent(max(block_format.indent() - 1, 0))
            cursor.setBlockFormat(block_format)

            cursor.endEditBlock()
            logging.info("Decreased indent level.")
             
    """----------File Operations----------"""
    def file_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open file", "", "Text documents (*.txt);;All files (*.*)")
        if path:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
            self.add_new_tab(text=text)  # Specify 'text' as a keyword argument
            index = self.tab_widget.currentIndex()
            self.paths[index] = path  # Track the path for the new tab
            filename = os.path.basename(path)
            self.tab_widget.setTabText(index, filename)
            self.tab_widget.setTabToolTip(index, path)

    def file_save(self, index=None):
        if index is None:
            index = self.tab_widget.currentIndex()

        path = self.paths.get(index)
        if path:
            self.save_file(path, index)
        else:
            self.file_saveas(index)

    def file_saveas(self, index=None):
        if index is None:
            index = self.tab_widget.currentIndex()

        path, _ = QFileDialog.getSaveFileName(self, "Save file", "", "Text documents (*.txt)")
        if path:
            self.save_file(path, index)

    def save_file(self, path, index):
        editor = self.tab_widget.widget(index)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(editor.toPlainText())
            self.paths[index] = path
            editor.document().setModified(False)
            filename = os.path.basename(path)
            self.tab_widget.setTabText(index, filename)
            self.tab_widget.setTabToolTip(index, path)
            logger.info(f"File saved: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")

    """----------Event Handling----------"""
    def closeEvent(self, event):
        """Save settings on close."""
        settings = {
            "window_size": [self.width(), self.height()],
            "window_position": [self.x(), self.y()],
            "theme": self.current_theme,
            "font_family": self.current_font_family,
            "font_size": self.current_font_size
        }
        save_settings(settings)
        event.accept() 

    """----------Capture Area Methods----------"""
    def set_capture_area(self):
        """Launch overlay for setting the capture area."""
        screens = QGuiApplication.screens()
        self.overlays = []

        def close_all_overlays(rect):
            for overlay in self.overlays:
                overlay.close()
            self.on_capture_area_set(rect)

        for screen in screens:
            screen_rect = screen.geometry()
            overlay = SnippingOverlay(screen_rect, close_all_callback=close_all_overlays)
            overlay.showFullScreen()
            overlay.activateWindow()
            overlay.raise_()
            self.overlays.append(overlay)

        logger.info("Snipping tool initialized on all screens.")

    def on_capture_area_set(self, snip_rect):
        """Set the capture area and update the flag."""
        self.capture_area = snip_rect
        self.capture_area_set = True  # Mark capture area as set
        logger.info(f"Capture area set to: {self.capture_area}")
        
        # If capturing was triggered by the capture button, proceed to capture the screen
        if self.capture_in_progress:
            self.capture()
            self.capture_in_progress = False  # Reset flag after capture

    def capture(self):
        """Capture the screen area if set; otherwise prompt user to set the area first."""
        if not hasattr(self, 'capture_in_progress'):
            self.capture_in_progress = False

        # If the capture area isn't set, prompt the user to set it
        if not self.capture_area_set:
            self.capture_in_progress = True  # Set flag to capture after area is set
            self.set_capture_area()
            return

        screens = QGuiApplication.screens()
        selected_screen = None
        for screen in screens:
            if screen.geometry().contains(self.capture_area.center()):
                selected_screen = screen
                break
        if not selected_screen:
            selected_screen = QGuiApplication.primaryScreen()

        # Adjust capture area to screen coordinates
        screen_rect = selected_screen.geometry()
        adjusted_x = self.capture_area.x() - screen_rect.x()
        adjusted_y = self.capture_area.y() - screen_rect.y()

        pixmap = selected_screen.grabWindow(0, adjusted_x, adjusted_y, self.capture_area.width(), self.capture_area.height())

        if not pixmap.isNull():
            editor = self.get_current_editor()
            if editor and isinstance(editor, QTextEdit):
                # Store image as a resource in the document to ensure persistence
                image_name = f"image_{QDateTime.currentDateTime().toString('yyyyMMddhhmmsszzz')}.png"
                image_url = QUrl(image_name)
                editor.document().addResource(QTextDocument.ResourceType.ImageResource, image_url, pixmap)

                # Define the image format for insertion
                image_format = QTextImageFormat()
                image_format.setName(image_url.toString())
                image_format.setWidth(self.capture_area.width())
                image_format.setHeight(self.capture_area.height())

                # Insert the image at the cursor position
                cursor = editor.textCursor()
                cursor.insertImage(image_format)
                logger.info("Captured area image inserted into document.")
        else:
            QMessageBox.warning(self, "Capture Failed", "Failed to capture the pre-set area.")
            
    """----------OCR Methods----------"""
    def perform_ocr(self):
        """Perform OCR with an overlay for user selection."""
        screens = QGuiApplication.screens()
        self.overlays = []

        def close_all_overlays(rect):
            for overlay in self.overlays:
                overlay.close()
            self.ocr_from_selected_area(rect)

        for screen in screens:
            screen_rect = screen.geometry()
            overlay = SnippingOverlay(screen_rect, close_all_callback=close_all_overlays)
            overlay.showFullScreen()
            overlay.activateWindow()
            overlay.raise_()
            self.overlays.append(overlay)

        logger.info("OCR overlay initialized.")

    def ocr_from_selected_area(self, snip_rect):
        """Capture selected area and perform OCR on it."""
        screens = QGuiApplication.screens()
        selected_screen = None
        for screen in screens:
            if screen.geometry().contains(snip_rect.center()):
                selected_screen = screen
                break
        if not selected_screen:
            selected_screen = QGuiApplication.primaryScreen()

        # Adjust capture area to screen coordinates
        screen_rect = selected_screen.geometry()
        adjusted_x = snip_rect.x() - screen_rect.x()
        adjusted_y = snip_rect.y() - screen_rect.y()

        pixmap = selected_screen.grabWindow(0, adjusted_x, adjusted_y, snip_rect.width(), snip_rect.height())

        if not pixmap.isNull():
            buffer = QBuffer()
            buffer.open(QBuffer.OpenModeFlag.ReadWrite)
            pixmap.save(buffer, "PNG")
            buffer.seek(0)

            # Convert QBuffer to BytesIO for Pillow compatibility
            image_data = BytesIO(buffer.data())
            pil_image = Image.open(image_data)

            # Perform OCR
            ocr_text = pytesseract.image_to_string(pil_image)

            # Insert OCR text into the editor without altering font settings
            editor = self.get_current_editor()
            if editor and isinstance(editor, QTextEdit):
                cursor = editor.textCursor()
                cursor.insertText(ocr_text)  # Inserts text using the current font
                logger.info("OCR text inserted into document.")
        else:
            QMessageBox.warning(self, "OCR Failed", "Failed to capture the selected area for OCR.")
              
    """----------Helper Methods----------"""
    def apply_format_to_selection_or_cursor(self, format):
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()

            # Apply background (highlight) color
            if format.background() != Qt.GlobalColor.transparent:
                background_format = QTextCharFormat()
                background_format.setBackground(format.background())
                cursor.mergeCharFormat(background_format)

            # Apply foreground (text color) independently
            if format.foreground() != QColor():
                foreground_format = QTextCharFormat()
                foreground_format.setForeground(format.foreground())
                cursor.mergeCharFormat(foreground_format)

            # Apply font weight (bold)
            if format.fontWeight() != QFont.Weight.Normal:
                bold_format = QTextCharFormat()
                bold_format.setFontWeight(format.fontWeight())
                cursor.mergeCharFormat(bold_format)

            # Apply italic
            if format.fontItalic():
                italic_format = QTextCharFormat()
                italic_format.setFontItalic(True)
                cursor.mergeCharFormat(italic_format)
            elif not format.fontItalic():
                italic_format = QTextCharFormat()
                italic_format.setFontItalic(False)
                cursor.mergeCharFormat(italic_format)

            # Apply underline
            if format.fontUnderline():
                underline_format = QTextCharFormat()
                underline_format.setFontUnderline(True)
                cursor.mergeCharFormat(underline_format)
            elif not format.fontUnderline():
                underline_format = QTextCharFormat()
                underline_format.setFontUnderline(False)
                cursor.mergeCharFormat(underline_format)

            # Apply strikethrough
            if format.fontStrikeOut():
                strikethrough_format = QTextCharFormat()
                strikethrough_format.setFontStrikeOut(True)
                cursor.mergeCharFormat(strikethrough_format)
            elif not format.fontStrikeOut():
                strikethrough_format = QTextCharFormat()
                strikethrough_format.setFontStrikeOut(False)
                cursor.mergeCharFormat(strikethrough_format)

            editor.setTextCursor(cursor)
            logger.info("Text formatting applied to selection or cursor position.")

# Main Application Execution
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Case and Note Organizer 2.0")
    window = MainWindow()
    window.show()
    logger.info("Application started.")
    sys.exit(app.exec())
